# Tải tư liệu miễn phí của Mixkit (giấy phép Mixkit: dùng miễn phí cho dự án thương mại, không cần ghi nguồn).
# Video: lấy bản 1080 (không có thì 720), cắt 12 giây đầu, bỏ tiếng, nén H.264 để nhẹ. Nhạc: tải nguyên bản mp3.
import json, os, subprocess, urllib.request
D = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(D, "out"); os.makedirs(OUT, exist_ok=True)
L = json.load(open(os.path.join(D, "list.json")))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Referer": "https://mixkit.co/"}
def get(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f: f.write(r.read())
for vid in L.get("video", []):
    dst = os.path.join(OUT, f"v{vid}.mp4")
    if os.path.exists(dst): continue
    tmp = f"/tmp/v{vid}.mp4"; ok = False
    for q in ("1080", "720"):
        try: get(f"https://assets.mixkit.co/videos/{vid}/{vid}-{q}.mp4", tmp); ok = True; print("video", vid, q); break
        except Exception as e: print("miss", vid, q, e)
    if not ok: continue
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-t", "12", "-an", "-vf", "scale=-2:1080", "-c:v", "libx264", "-crf", "24", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst], check=False)
for mid in L.get("music", []):
    dst = os.path.join(OUT, f"m{mid}.mp3")
    if os.path.exists(dst): continue
    try: get(f"https://assets.mixkit.co/music/{mid}/{mid}.mp3", dst); print("music", mid)
    except Exception as e: print("miss music", mid, e)
for name, url in (L.get("urls") or {}).items():   # tệp riêng của chủ dự án (link có hạn ngắn) – tải nguyên bản
    dst = os.path.join(OUT, name)
    if os.path.exists(dst): continue
    try: get(url, dst); print("file", name)
    except Exception as e: print("miss file", name, type(e).__name__)

# Ô ảnh vệ tinh cho cảnh bản đồ 3D: {"tiles": {"name": "kp-sat", "url": "...{z}/{y}/{x}", "boxes": [[z, lat0, lon0, lat1, lon1], ...]}} -> out/<name>.tar
import math, tarfile, io, time
T = L.get("tiles")
if T and not os.path.exists(os.path.join(OUT, T["name"] + ".tar")):
    def tx(lon, z): return int((lon + 180) / 360 * 2 ** z)
    def ty(lat, z): r = math.radians(lat); return int((1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z)
    want = set()
    for z, a0, o0, a1, o1 in T["boxes"]:
        for x in range(tx(o0, z), tx(o1, z) + 1):
            for y in range(ty(a1, z), ty(a0, z) + 1): want.add((z, x, y))
    print("tiles", len(want))
    with tarfile.open(os.path.join(OUT, T["name"] + ".tar"), "w") as tf:
        for (z, x, y) in sorted(want):
            for k in range(3):
                try:
                    req = urllib.request.Request(T["url"].format(z=z, x=x, y=y), headers={"User-Agent": UA["User-Agent"]})
                    with urllib.request.urlopen(req, timeout=60) as r: b = r.read()
                    ti = tarfile.TarInfo(f"{z}/{x}/{y}.jpg"); ti.size = len(b); tf.addfile(ti, io.BytesIO(b)); break
                except Exception as e: print("miss", z, x, y, type(e).__name__); time.sleep(1)
# Dữ liệu OpenStreetMap (sông, địa danh) cho cảnh bản đồ: {"overpass": {"name": "kp-osm", "q": "..."}} -> out/<name>.json
O = L.get("overpass")
if O and not os.path.exists(os.path.join(OUT, O["name"] + ".json")):
    import urllib.parse
    data = urllib.parse.urlencode({"data": O["q"]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter", data=data, headers={"User-Agent": "micc-studio-fetch"}), timeout=180) as r:
            open(os.path.join(OUT, O["name"] + ".json"), "wb").write(r.read()); print("osm ok")
    except Exception as e: print("osm miss", e)
