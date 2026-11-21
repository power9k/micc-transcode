# -*- coding: utf-8 -*-
"""Bản đồ 3D chân thực cho project CapCut (chủ dặn 21/11): ảnh vệ tinh thật + địa hình + nhà 3D, camera bay vòng hạ dần vào địa điểm, ghim + tên địa điểm kiểu sang trọng.
Dựng bằng MapLibre GL trong Chrome không màn hình (Playwright), chụp từng khung → ffmpeg ra mp4 9:16."""
import os, json, math, subprocess, shutil, time, urllib.request, urllib.parse

UA = 'micc-media-map/1.0'
HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<style>html,body,#m{margin:0;width:100%;height:100%;background:#0b0f18;overflow:hidden}
#pin{position:absolute;left:50%;top:46%;transform:translate(-50%,-100%);display:flex;flex-direction:column;align-items:center;opacity:0;transition:none}
#pin .lb{padding:18px 34px;border-radius:999px;background:linear-gradient(180deg,rgba(20,26,40,.92),rgba(10,14,24,.92));box-shadow:0 0 0 2px rgba(233,191,98,.85),0 18px 40px rgba(0,0,0,.55);
font:800 46px/1.1 'Segoe UI',Arial,sans-serif;color:#f6e3a8;letter-spacing:.02em;white-space:nowrap}
#pin .sb{margin-top:8px;font:600 30px/1.2 'Segoe UI',Arial,sans-serif;color:#e8ecf4;text-shadow:0 2px 10px #000;white-space:nowrap}
#pin .st{width:4px;height:120px;background:linear-gradient(#e9bf62,rgba(233,191,98,0))}
#pin .dot{width:30px;height:30px;border-radius:50%;background:#e9bf62;box-shadow:0 0 0 10px rgba(233,191,98,.25),0 0 40px 12px rgba(233,191,98,.6);margin-top:-6px}
#vig{position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 55%,rgba(0,0,0,.55))}
</style></head><body><div id="m"></div><div id="vig"></div>
<div id="pin"><div class="lb"></div><div class="sb"></div><div class="st"></div><div class="dot"></div></div>
<script>
const P = window.__P;
document.querySelector('#pin .lb').textContent = P.name || '';
document.querySelector('#pin .sb').textContent = P.sub || '';
const map = new maplibre.Map({container: 'm', interactive: false, attributionControl: false, fadeDuration: 0, maxPitch: 85, preserveDrawingBuffer: true,
  center: [P.lon, P.lat], zoom: P.z0, pitch: P.p0, bearing: P.b0,
  style: {version: 8, glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      sat: {type: 'raster', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], tileSize: 256, maxzoom: 19},
      dem: {type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'], encoding: 'terrarium', tileSize: 256, maxzoom: 14},
      ofm: {type: 'vector', url: 'https://tiles.openfreemap.org/planet'}},
    layers: [
      {id: 'sat', type: 'raster', source: 'sat', paint: {'raster-saturation': 0.12, 'raster-contrast': 0.12, 'raster-brightness-max': 0.95}},
      {id: 'b3d', type: 'fill-extrusion', source: 'ofm', 'source-layer': 'building', minzoom: 14,
       paint: {'fill-extrusion-color': ['interpolate', ['linear'], ['coalesce', ['get', 'render_height'], 8], 0, '#cfd3da', 60, '#e9e2d0', 200, '#f3e3b8'],
               'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 8], 'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0], 'fill-extrusion-opacity': 0.86}}],
    sky: {'sky-color': '#7fa6d6', 'horizon-color': '#f2d9b0', 'fog-color': '#c9d6e6', 'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.6, 'fog-ground-blend': 0.25}}
});
map.on('load', () => { try { map.setTerrain({source: 'dem', exaggeration: 1.3}); } catch (e) {} window.__ready = true; });
window.__go = (f) => new Promise(res => {
  const c = window.__cam(f); map.jumpTo(c.cam);
  const pin = document.getElementById('pin'); pin.style.opacity = c.pin; pin.style.transform = 'translate(-50%,-100%) translateY(' + (1 - c.pin) * 40 + 'px)';
  let done = false; const fin = () => { if (!done) { done = true; res(); } };
  if (map.areTilesLoaded && map.areTilesLoaded() && !map.isMoving()) requestAnimationFrame(() => requestAnimationFrame(fin)); else { map.once('idle', fin); setTimeout(fin, P.wait); }
});
window.__cam = (f) => { const u = f / Math.max(1, P.n - 1), e = u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
  return {cam: {center: [P.lon, P.lat], zoom: P.z0 + (P.z1 - P.z0) * e, pitch: P.p0 + (P.p1 - P.p0) * e, bearing: P.b0 + (P.b1 - P.b0) * u}, pin: Math.max(0, Math.min(1, (u - .35) / .2))}; };
</script></body></html>"""


def geocode(q, log=print):
    try:
        u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 1, 'countrycodes': 'vn'})
        j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=20).read())
        if j: return float(j[0]['lat']), float(j[0]['lon'])
    except Exception as e: log('  bản đồ: không tìm được toạ độ', q, e)
    return None


def _browser():
    for p in (os.environ.get('MG_BROWSER'), '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/opt/pw-browsers/chromium'):
        if p and os.path.exists(p): return p
    return None


def render(lat, lon, dur, out, name='', sub='', w=1080, h=1920, fps=30, seed=0, log=print):
    try: from playwright.sync_api import sync_playwright
    except Exception:
        subprocess.run(['pip', 'install', '-q', 'playwright'], capture_output=True, timeout=300); from playwright.sync_api import sync_playwright
    n = max(30, int(round(dur * fps))); rot = 35 + (seed * 17) % 40; sgn = -1 if seed % 2 else 1
    P = dict(lat=lat, lon=lon, name=name, sub=sub, n=n, z0=12.6, z1=16.4, p0=25, p1=68, b0=(seed * 47) % 360, b1=(seed * 47) % 360 + sgn * rot, wait=6000)
    wd = out + '_f'; shutil.rmtree(wd, ignore_errors=True); os.makedirs(wd)
    t0 = time.time()
    with sync_playwright() as pw:
        exe = _browser(); args = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox']
        b = pw.chromium.launch(executable_path=exe, args=args) if exe else pw.chromium.launch(args=args)
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
        pg.add_init_script('window.__P = %s;' % json.dumps(P, ensure_ascii=False))
        pg.set_content(HTML, wait_until='load', timeout=60000)
        pg.wait_for_function('window.__ready === true', timeout=60000)
        pg.evaluate('window.__go(0)'); time.sleep(1.5); pg.evaluate('window.__go(0)')   # chờ ô bản đồ đầu tải xong
        for f in range(n):
            pg.evaluate('(f) => window.__go(f)', f)
            pg.screenshot(path=os.path.join(wd, '%05d.jpg' % f), type='jpeg', quality=92)
        b.close()
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', str(fps), '-i', os.path.join(wd, '%05d.jpg'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', '-movflags', '+faststart', out], capture_output=True, text=True)
    shutil.rmtree(wd, ignore_errors=True)
    if not os.path.exists(out): raise RuntimeError('bản đồ 3D: ffmpeg lỗi ' + r.stderr[-200:])
    log('  bản đồ 3D “%s” %.1fs dựng trong %ds' % (name, dur, time.time() - t0))
    return out
