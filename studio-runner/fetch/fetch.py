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
