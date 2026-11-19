"""Local HTTP shim: serves a large public Drive file to ffmpeg using only closed byte ranges.

Drive answers an open-ended `Range: bytes=N-` on a very large shared file with a
"Quota exceeded" HTML page, but still serves closed ranges. ffmpeg always asks for
open-ended ranges, so this shim accepts those and fetches the bytes upstream in
fixed-size closed chunks, streaming them back until ffmpeg hangs up (it does so on seek).

usage: python rangeproxy.py <drive_file_id> <port>
"""
import http.server
import socketserver
import ssl
import sys
import time
import urllib.request

FILE_ID, PORT = sys.argv[1], int(sys.argv[2])
URL = f"https://drive.usercontent.google.com/download?id={FILE_ID}&export=download&confirm=t"
CHUNK = 8 * 1024 * 1024
import os
CA = "/root/.ccr/ca-bundle.crt"
CTX = ssl.create_default_context(cafile=CA) if os.access(CA, os.R_OK) else ssl.create_default_context()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler(), urllib.request.HTTPSHandler(context=CTX))


def fetch(a, b):
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL, headers={"Range": f"bytes={a}-{b}", "User-Agent": "curl/8.5.0"})
            with OPENER.open(req, timeout=60) as r:
                if r.status != 206 or not r.headers.get("Content-Type", "").startswith("video/"):
                    raise IOError(f"unexpected {r.status} {r.headers.get('Content-Type')}")
                return r.read()
        except Exception as e:  # transient network/quota hiccup: back off and retry
            sys.stderr.write(f"fetch {a}-{b} failed ({e}); retry {attempt + 1}\n")
            time.sleep(2 + attempt * 3)
    raise IOError(f"giving up on {a}-{b}")


def total_size():
    req = urllib.request.Request(URL, headers={"Range": "bytes=0-0", "User-Agent": "curl/8.5.0"})
    with OPENER.open(req, timeout=60) as r:
        return int(r.headers["Content-Range"].split("/")[1])


TOTAL = total_size()


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _range(self):
        rng = self.headers.get("Range", "bytes=0-")
        a, _, b = rng.replace("bytes=", "").partition("-")
        a = int(a or 0)
        b = int(b) if b else TOTAL - 1
        return a, min(b, TOTAL - 1)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(TOTAL))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def do_GET(self):
        a, b = self._range()
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {a}-{b}/{TOTAL}")
        self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        pos = a
        try:
            while pos <= b:
                end = min(pos + CHUNK - 1, b)
                self.wfile.write(fetch(pos, end))
                pos = end + 1
        except (BrokenPipeError, ConnectionResetError):
            pass  # ffmpeg seeked elsewhere


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


print(f"serving {TOTAL} bytes on 127.0.0.1:{PORT}", flush=True)
S(("127.0.0.1", PORT), H).serve_forever()
