# AI lọc source (bản 242): mỗi thư mục con của thư mục “Source” (1 buổi quay) → thư mục “Lọc”
# 1) Đọc từng video thẳng từ Drive (không lưu cả kho): âm thanh 16 kHz + ảnh khung chính (keyframe) → độ nét, sáng, rung
# 2) Chép lời có mốc từng chữ (faster-whisper)  3) Gemini xem ảnh + lời → hiểu kịch bản, chọn bản tốt nhất, đoạn giữ lại
# 4) A-roll (có thoại): cắt bỏ ngắt nghỉ, ầm à, nối liền 1 video, giữ độ phân giải gốc  5) B-roll: cắt không nén lại (giữ nguyên chất lượng)
import os, sys, json, time, re, subprocess, base64, glob, shutil, random, urllib.request, urllib.error, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from PIL import Image

API, SEC = os.environ['MICC_API'], os.environ['MICC_SECRET']
T0, MAXMIN = time.time(), float(os.environ.get('MAX_MIN', '320'))
TMP = os.environ.get('LOC_TMP', '/tmp/loc')
WM = os.environ.get('LOC_WHISPER', 'small')
G = 'https://www.googleapis.com'
GEM = 'https://generativelanguage.googleapis.com/v1beta/'
AP = {'by': 'ai-loc', 'byName': 'AI lọc source', 'via': 'loc'}
FILL = {'ừ', 'ừm', 'ờ', 'ờm', 'ơ', 'à', 'ầm', 'ậm', 'hừm', 'ừa', 'um', 'uhm', 'uh', 'ah', 'eh', 'hmm', 'ưm', 'ừ ừ', 'ơ ơ'}

def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)

def http(url, data=None, headers=None, method=None, timeout=300, raw=False):
    h = dict(headers or {})
    if data is not None and not isinstance(data, (bytes, bytearray)):
        data = json.dumps(data).encode(); h.setdefault('Content-Type', 'application/json')
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
        return (r, b) if raw else (json.loads(b) if b else {})

def api(action, **b):
    for i in range(4):
        try:
            j = http(API, dict(action=action, s=SEC, **b), timeout=180)
            if j.get('ok') is False: raise RuntimeError(j.get('error') or 'lỗi máy chủ')
            return j
        except Exception as e:
            if i == 3: raise
            log('  máy chủ lỗi, thử lại:', e); time.sleep(3 * (i + 1))

TK = {'v': None, 't': 0}
def tok():
    if time.time() - TK['t'] > 1500: TK['v'] = api('pxToken')['token']; TK['t'] = time.time()
    return TK['v']
def drive(path, data=None, method=None, params='supportsAllDrives=true'):
    for i in range(5):
        try: return http(G + '/drive/v3/' + path + ('?' + params if params else ''), data, {'Authorization': 'Bearer ' + tok()}, method)
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429: raise RuntimeError('Drive %s: %s' % (e.code, e.read()[:200]))
            time.sleep(2 * (i + 1))
    raise RuntimeError('Drive không phản hồi')
def durl(fid): return G + '/drive/v3/files/' + fid + '?alt=media&supportsAllDrives=true'
def fin(fid, ss=None, t=None):
    a = ['-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5']
    if ss is not None: a += ['-ss', '%.3f' % ss]
    if t is not None: a += ['-t', '%.3f' % t]
    return a + ['-headers', 'Authorization: Bearer %s\r\n' % tok(), '-i', durl(fid)]
def run(cmd, timeout=None):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0: raise RuntimeError((cmd[0] + ': ' + p.stderr.strip().splitlines()[-1]) if p.stderr.strip() else cmd[0] + ' lỗi')
    return p

def download(fid, size, dst):
    got = 0
    if os.path.exists(dst): os.remove(dst)
    for tries in range(8):
        try:
            req = urllib.request.Request(durl(fid), headers={'Authorization': 'Bearer ' + tok(), 'Range': 'bytes=%d-' % got})
            with urllib.request.urlopen(req, timeout=120) as r, open(dst, 'ab') as w:
                if r.status == 200 and got: w.truncate(0); got = 0
                while True:
                    b = r.read(8 << 20)
                    if not b: break
                    w.write(b); got += len(b)
            if not size or got >= size: return
        except Exception as e:
            log('  tải lỗi, thử lại:', e); time.sleep(3 * (tries + 1))
    if size and got < size: raise RuntimeError('tải video không đủ (%d/%d)' % (got, size))

# ---------- 1) xem + nghe từng video ----------
def gray(path):
    im = Image.open(path).convert('L'); im.thumbnail((256, 256)); return np.asarray(im, dtype=np.float32)
def lap(a): return float(np.var(4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]))
def shift(a, b):
    if a.shape != b.shape: return 0.0
    F = np.fft.fft2(a - a.mean()) * np.conj(np.fft.fft2(b - b.mean())); F /= np.abs(F) + 1e-6
    c = np.abs(np.fft.ifft2(F)); y, x = np.unravel_index(np.argmax(c), c.shape); h, w = a.shape
    y = y - h if y > h // 2 else y; x = x - w if x > w // 2 else x
    return float(np.hypot(x, y)) / w
def analyze(i, v):
    d = os.path.join(TMP, 'a%03d' % i); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    pr = json.loads(run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams'] + fin(v['id'])[-4:], timeout=120).stdout or '{}')
    vs = next((s for s in pr.get('streams', []) if s.get('codec_type') == 'video'), {})
    has_a = any(s.get('codec_type') == 'audio' for s in pr.get('streams', []))
    dur = float(pr.get('format', {}).get('duration') or v.get('dur') or 0)
    cmd = ['ffmpeg', '-y', '-v', 'info', '-skip_frame', 'nokey'] + fin(v['id'])
    if has_a: cmd += ['-map', '0:a:0', '-ac', '1', '-ar', '16000', os.path.join(d, 'a.wav')]
    cmd += ['-map', '0:v:0', '-vf', 'scale=320:-2,showinfo', '-fps_mode', 'vfr', '-q:v', '5', os.path.join(d, 'k%05d.jpg')]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    kt = [float(m) for m in re.findall(r'pts_time:\s*([\d.]+)', p.stderr)]
    ims = sorted(glob.glob(os.path.join(d, 'k*.jpg')))
    if not ims: raise RuntimeError('không đọc được hình video “%s”' % v['name'])
    kt = (kt + [0] * len(ims))[:len(ims)]
    g = [gray(x) for x in ims]
    sharp = [lap(x) for x in g]; bright = [float(x.mean()) for x in g]
    mot = [0.0] + [shift(g[k - 1], g[k]) / max(.2, kt[k] - kt[k - 1]) for k in range(1, len(g))]
    pick = sorted(set([0, len(ims) // 2, len(ims) - 1, len(ims) // 4, 3 * len(ims) // 4]))[:4]
    thumbs = []
    for k in pick:
        im = Image.open(ims[k]).convert('RGB'); im.thumbnail((288, 288)); bio = __import__('io').BytesIO(); im.save(bio, 'JPEG', quality=60)
        thumbs.append([round(kt[k], 1), base64.b64encode(bio.getvalue()).decode()])
    return dict(i=i, name=v['name'], id=v['id'], size=v.get('size') or 0, dur=dur, w=vs.get('width'), h=vs.get('height'), codec=vs.get('codec_name'),
                wav=os.path.join(d, 'a.wav') if has_a and os.path.exists(os.path.join(d, 'a.wav')) else None, kt=kt, sharp=sharp, bright=bright, mot=mot, thumbs=thumbs, dir=d)

ASR = {}
def transcribe(wav):
    if not wav: return []
    if 'm' not in ASR:
        from faster_whisper import WhisperModel
        ASR['m'] = WhisperModel(WM, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 4)
    segs, _ = ASR['m'].transcribe(wav, beam_size=1, vad_filter=True, word_timestamps=True, condition_on_previous_text=False)
    out = []
    for s in segs:
        ws = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for w in (s.words or []) if w.word.strip()]
        out.append(dict(s=round(s.start, 2), e=round(s.end, 2), t=s.text.strip(), w=ws))
    return out

def summary(a):
    sh = np.array(a['sharp'] or [0]); ref = float(np.median(sh)) or 1
    bad = []
    for k, t in enumerate(a['kt']):
        why = 'rung' if a['mot'][k] > .06 else 'mờ' if a['sharp'][k] < ref * .35 else 'tối' if a['bright'][k] < 25 else 'cháy sáng' if a['bright'][k] > 235 else ''
        if why: bad.append((t, why))
    ivs = []
    for t, why in bad:
        if ivs and ivs[-1][2] == why and t - ivs[-1][1] < 2.5: ivs[-1][1] = t
        else: ivs.append([t, t, why])
    q = ', '.join('%.0f-%.0fs %s' % (x[0], x[1] + 1, x[2]) for x in ivs[:12]) or 'ổn định, nét'
    tx = ' '.join('[%.1f-%.1f] %s' % (s['s'], s['e'], s['t']) for s in a['segs'])
    return 'VIDEO #%d · tên "%s" · %.1f giây · %sx%s · độ nét TB %.0f · chất lượng hình: %s\nLời thoại: %s' % (a['i'], a['name'], a['dur'], a['w'], a['h'], ref, q, tx[:3500] or '(không có lời)')

# ---------- 3) Gemini lên kế hoạch lọc ----------
SYS = '''Bạn là video editor chuyên nghiệp của team truyền thông bất động sản MICC. Bạn nhận toàn bộ source (cảnh quay gốc) của 1 buổi quay: ảnh khung hình, chất lượng hình, lời thoại có mốc thời gian.
Nhiệm vụ: LỌC SOURCE như editor lọc tay trước khi dựng.
1. Hiểu buổi quay nhằm mục đích gì, kịch bản / lời thoại chung là gì.
2. Phân loại: A-roll = cảnh có người nói theo kịch bản (MC, phỏng vấn, thuyết trình); B-roll = cảnh minh họa không thoại chính (toàn cảnh, cận cảnh, chi tiết, flycam…).
3. Cảnh quay lại nhiều lần (cùng góc / cùng nội dung / cùng câu thoại): chỉ chọn 1 bản tốt nhất – nét, ổn định, bố cục đẹp, nói trôi chảy, đủ ý nhất. Bỏ hẳn các bản kém, bản hỏng, bản quay nhầm.
4. Với mỗi video được chọn, ghi các đoạn GIỮ LẠI (giây, theo video gốc): bỏ đoạn rung lắc, mờ, chuẩn bị, chờ, nói linh tinh ngoài kịch bản, nói hỏng rồi nói lại (chỉ giữ lần nói đúng cuối cùng). A-roll giữ trọn câu, không cắt giữa câu. B-roll giữ đoạn đẹp, ổn định nhất (thường 3–15 giây; nhiều đoạn đẹp khác nhau thì giữ nhiều đoạn).
5. Mỗi video gốc dùng tối đa 1 lần. Thứ tự: A-roll theo đúng mạch kịch bản; B-roll theo mạch hình ảnh hợp lý.
6. Đặt tên ngắn gọn tiếng Việt có dấu mô tả nội dung (không đuôi, không số thứ tự), vd "MC giới thiệu tổng quan dự án", "Toàn cảnh hồ bơi lúc hoàng hôn".
Trả về JSON đúng dạng: {"muc_dich":"1 câu mục đích buổi quay","clips":[{"loai":"A"|"B","video":<số #>,"giu":[[giây_bắt_đầu,giây_kết_thúc],...],"ten":"..."}]}'''

def gemini(key, models, data):
    parts = [{'text': 'Buổi quay: %s\nCó %d video:' % (data['title'], len(data['vids']))}]
    for a in data['vids']:
        parts.append({'text': summary(a)})
        for t, b in a['thumbs']: parts += [{'text': '#%d lúc %.1fs:' % (a['i'], t)}, {'inline_data': {'mime_type': 'image/jpeg', 'data': b}}]
    body = {'systemInstruction': {'parts': [{'text': SYS}]}, 'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'temperature': .2, 'maxOutputTokens': 30000, 'responseMimeType': 'application/json'}}
    last = ''
    for rnd in range(4):
        for m in models:
            try:
                j = http(GEM + 'models/' + m + ':generateContent', body, {'x-goog-api-key': key}, timeout=600)
                txt = ''.join(p.get('text', '') for p in ((j.get('candidates') or [{}])[0].get('content') or {}).get('parts', []))
                plan = json.loads(re.sub(r'^```(json)?|```$', '', txt.strip()))
                if plan.get('clips'): log('  Gemini (%s): %d file lọc' % (m, len(plan['clips']))); return plan
                last = m + ': kế hoạch rỗng'
            except urllib.error.HTTPError as e: last = '%s: %s %s' % (m, e.code, e.read()[:160])
            except Exception as e: last = '%s: %s' % (m, e)
            log('  Gemini lỗi:', last)
        time.sleep(20 * (rnd + 1))
    raise RuntimeError('Gemini không trả kế hoạch (' + last + ')')

def fallback(vids):  # khi Gemini không được: video có thoại = A, không thoại = B (bỏ đầu / cuối rung)
    cl = []
    for a in vids:
        sp = sum(len(s['w']) for s in a['segs'])
        good = [t for k, t in enumerate(a['kt']) if a['mot'][k] <= .06]
        s0, e0 = (min(good), max(good) + 1) if good else (0, a['dur'])
        cl.append({'loai': 'A' if sp >= 8 else 'B', 'video': a['i'], 'giu': [[0, a['dur']]] if sp >= 8 else [[s0, min(e0, a['dur'])]], 'ten': os.path.splitext(a['name'])[0]})
    return {'muc_dich': '', 'clips': sorted(cl, key=lambda c: c['loai'])}

# ---------- 4) cắt ghép ----------
def norm(w): return re.sub(r'[^\w\s]', '', unicodedata.normalize('NFC', w.lower())).strip()
def refine(words, keep):
    segs = []
    for s, e in keep:
        ws = [w for w in words if w[0] >= s - .25 and w[1] <= e + .25]
        ws = [w for k, w in enumerate(ws) if not (norm(w[2]) in FILL and w[1] - w[0] < 1.2) and not (k + 1 < len(ws) and norm(w[2]) and norm(w[2]) == norm(ws[k + 1][2]) and ws[k + 1][0] - w[1] < .4)]
        if not ws: continue
        cur = [max(s, ws[0][0] - .15), ws[0][1]]
        for w in ws[1:]:
            if w[0] - cur[1] > .55: cur[1] = min(cur[1] + .2, w[0] - .05); segs.append(cur); cur = [max(cur[1], w[0] - .15), w[1]]
            else: cur[1] = w[1]
        cur[1] = min(e, cur[1] + .3); segs.append(cur)
    out = []
    for a, b in segs:
        if b - a < .25: continue
        if out and a - out[-1][1] < .08: out[-1][1] = b
        else: out.append([a, b])
    return out
def safe(n): return re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', n).strip()[:90] or 'Cảnh'

def make_a(a, segs, src, out):  # nối các đoạn giữ lại thành 1 video (concat demuxer: mở từng đoạn lần lượt, không tốn RAM)
    lst = out + '.txt'; q = src.replace("'", "'\\''")
    open(lst, 'w').write(''.join("file '%s'\ninpoint %.3f\noutpoint %.3f\n" % (q, s, e) for s, e in segs))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'format=yuv420p',
           '-c:v', 'libx264', '-preset', os.environ.get('LOC_PRESET', 'ultrafast'), '-crf', os.environ.get('LOC_CRF', '14'),
           '-af', 'aresample=async=1:first_pts=0', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-threads', '0', out]
    run(cmd, timeout=5400); os.remove(lst)

def make_b(a, keep, src, out):
    kt = sorted(a['kt']); parts = []
    for k, (s, e) in enumerate(keep):
        ks = next((t for t in kt if t >= s - .05), None)
        if ks is None or e - ks < .8: ks = max([t for t in kt if t <= s] or [0])
        pth = out + '.p%02d%s' % (k, os.path.splitext(out)[1])
        run(['ffmpeg', '-y', '-v', 'error', '-ss', '%.3f' % ks, '-i', src, '-t', '%.3f' % (e - ks), '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy', '-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', pth], timeout=1800)
        parts.append(pth)
    if len(parts) == 1: os.replace(parts[0], out); return
    lst = out + '.txt'; open(lst, 'w').write(''.join("file '%s'\n" % p.replace("'", "'\\''") for p in parts))
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', out], timeout=1800)
    for p in parts + [lst]: os.remove(p)

def upload(path, name, parent):
    size = os.path.getsize(path)
    mt = 'video/quicktime' if path.lower().endswith('.mov') else 'video/mp4'
    for i in range(5):
        try:
            r, _ = http(G + '/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=id', {'name': name, 'parents': [parent], 'appProperties': AP},
                        {'Authorization': 'Bearer ' + tok(), 'X-Upload-Content-Type': mt, 'X-Upload-Content-Length': str(size)}, raw=True)
            url = r.headers['Location']; pos = 0
            with open(path, 'rb') as f:
                while True:
                    f.seek(pos); b = f.read(64 << 20)
                    req = urllib.request.Request(url, data=b, method='PUT', headers={'Content-Range': 'bytes %d-%d/%d' % (pos, pos + len(b) - 1, size) if size else 'bytes */0'})
                    try:
                        with urllib.request.urlopen(req, timeout=600) as rr: return json.loads(rr.read())['id']
                    except urllib.error.HTTPError as e:
                        if e.code != 308: raise
                        rg = e.headers.get('Range'); pos = int(rg.split('-')[1]) + 1 if rg else pos + len(b)
        except Exception as e:
            log('  tải lên lỗi, thử lại:', e); time.sleep(4 * (i + 1))
    raise RuntimeError('không tải được “%s” lên Drive' % name)

# ---------- 1 buổi quay ----------
def job(j, key, models):
    t0 = time.time(); jb = j['job']; vids = jb['videos']; title = (jb.get('src') or '') + ' › ' + jb['name']
    log('▶ Lọc', title, '·', len(vids), 'video')
    shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
    res = {}
    with ThreadPoolExecutor(4) as ex:
        fs = {ex.submit(analyze, i + 1, v): i + 1 for i, v in enumerate(vids)}
        for f in as_completed(fs):
            try: a = f.result()
            except Exception as e: log('  bỏ qua video #%d: %s' % (fs[f], e)); continue
            a['segs'] = transcribe(a['wav']); res[a['i']] = a
            log('  ✓ đã xem + nghe #%d %s (%.0fs, %d câu)' % (a['i'], a['name'], a['dur'], len(a['segs'])))
    A = [res[k] for k in sorted(res)]
    if not A: raise RuntimeError('không đọc được video nào')
    log('  xem + nghe xong sau %.1f phút' % ((time.time() - t0) / 60))
    try: plan = gemini(key, models, {'title': title, 'vids': A})
    except Exception as e: log('  ', e, '→ dùng cách lọc đơn giản'); plan = fallback(A)
    by = {a['i']: a for a in A}; seen = set(); clips = []
    for c in plan.get('clips') or []:
        try: vi = int(c.get('video'))
        except Exception: continue
        if vi not in by or vi in seen: continue
        a = by[vi]; keep = []
        for r in c.get('giu') or [[0, a['dur']]]:
            try: s, e = max(0.0, float(r[0])), min(a['dur'], float(r[1]))
            except Exception: continue
            if e - s >= .8: keep.append([s, e])
        if not keep: continue
        seen.add(vi); clips.append(dict(t='A' if str(c.get('loai', 'B')).upper().startswith('A') else 'B', a=a, keep=sorted(keep), name=safe(str(c.get('ten') or os.path.splitext(a['name'])[0]))))
    if not clips: raise RuntimeError('kế hoạch lọc không có file nào')
    loc = drive('files', {'name': '_AI đang lọc…', 'mimeType': 'application/vnd.google-apps.folder', 'parents': [jb['fid']], 'appProperties': AP}, params='supportsAllDrives=true&fields=id')['id']
    try:
        na = nb = 0
        for c in clips:
            a = c['a']; c['n'] = (na := na + 1) if c['t'] == 'A' else (nb := nb + 1)
            ext = os.path.splitext(a['name'])[1].lower() if c['t'] == 'B' else '.mp4'
            ext = ext if ext in ('.mp4', '.mov', '.m4v') else '.mp4'
            nm = '%s%02d - %s%s' % (c['t'], c['n'], c['name'], ext)
            whole = len(c['keep']) == 1 and c['keep'][0][0] < .3 and c['keep'][0][1] > a['dur'] - .3
            if c['t'] == 'B' and whole:
                drive('files/%s/copy' % a['id'], {'name': nm, 'parents': [loc], 'appProperties': AP}, params='supportsAllDrives=true&fields=id'); log('  ✓', nm, '(chép nguyên bản)'); continue
            src = os.path.join(TMP, 'src_%03d%s' % (a['i'], os.path.splitext(a['name'])[1].lower() or '.mp4'))
            download(a['id'], a['size'], src); out = os.path.join(TMP, 'out%s' % ext)
            if c['t'] == 'A':
                words = [w for s in a['segs'] for w in s['w']]
                segs = refine(words, c['keep']) if words else c['keep']
                make_a(a, segs or c['keep'], src, out)
            else: make_b(a, c['keep'], src, out)
            upload(out, nm, loc); os.remove(out); os.remove(src)
            log('  ✓', nm)
        drive('files/' + loc, {'name': 'Lọc'}, method='PATCH')
    except Exception:
        try: drive('files/' + loc, method='DELETE')
        except Exception: pass
        raise
    secs = time.time() - t0
    api('locDone', fid=jb['fid'], out=loc, name=jb['name'], src=jb.get('src') or '', n=na + nb, na=na, nb=nb, vin=len(vids), secs=round(secs), last=jb.get('last') or 0, goal=plan.get('muc_dich') or '')
    log('✓ Xong', title, '· %d file · %.1f phút' % (na + nb, secs / 60))

NEED = 242
def ensure():  # máy chủ chưa lên bản có AI lọc → nhờ máy chủ tự cập nhật từ web, chờ tới khi xong
    for k in range(int(os.environ.get('LOC_WAIT', '56'))):  # chờ tối đa ~4,7 giờ (máy chủ hết hạn mức gọi mạng thì phải chờ Google cấp lại)
        try:
            j = api('cgCheck', v='MICC Bot bản %d' % NEED, uf=1, site=os.environ.get('MICC_SITE', 'https://miccmedia.edgeone.dev'))
            if j.get('uf'): log('Lượt gọi mạng máy chủ 24 giờ qua:', j['uf'].get('total'), '· theo giờ (mới → cũ):', j['uf'].get('hours'), '\n  ' + '\n  '.join(j['uf'].get('top') or []))
            n = int((re.search(r'(\d+)', j.get('ver') or '') or [0, 0])[1] or 0) if re.search(r'(\d+)', j.get('ver') or '') else 0
            log('Máy chủ:', j.get('ver'), '·', j.get('err') or '', '·', ' | '.join(j.get('last') or []))
            if n >= NEED: return True
        except Exception as e: log('  kiểm tra máy chủ lỗi:', e)
        time.sleep(300 if k else 60)
    return False

def main():
    done = 0
    if not ensure(): log('Máy chủ chưa lên bản %d, dừng.' % NEED); sys.exit(1)
    while (time.time() - T0) / 60 < MAXMIN - 45:
        j = api('locJobs')
        if not j.get('job'): break
        try: job(j, j.get('key') or '', j.get('models') or ['gemini-flash-latest'])
        except Exception as e:
            log('✗ lỗi:', e)
            try: api('locDone', fid=j['job']['fid'], name=j['job']['name'], fail=str(e)[:300])
            except Exception: pass
        done += 1
    log('Hết việc lọc (%d buổi quay)' % done)

if __name__ == '__main__': main()
