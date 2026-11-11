# AI lọc source (bản 244): mỗi thư mục con của thư mục “Source” (1 buổi quay) → thư mục “Lọc”
# CHẠY ĐỘC LẬP với máy chủ Apps Script (không dính hạn mức gọi mạng của Google Apps Script):
#  - tự quét Drive (GitHub chạy 10 phút / lần), trạng thái ghi ngay trên Drive (appProperties của thư mục buổi quay)
#  - khóa Gemini + Zalo lấy từ gói máy chủ mã hóa trên web (cg.bin, giải bằng MICC_SECRET); máy chủ chỉ dùng để xin mã Drive (pxToken)
#  - tự gửi tin Zalo vào nhóm test (mã nhóm lấy từ máy chủ khi máy chủ khỏe, lưu trên thư mục kho để dùng cả khi máy chủ hết hạn mức)
# 1) Đọc từng video thẳng từ Drive: âm thanh 16 kHz + ảnh khung chính (keyframe) → độ nét, sáng, rung
# 2) Chép lời có mốc từng chữ (faster-whisper)  3) Gemini xem ảnh + lời → hiểu kịch bản, chọn bản tốt nhất, đoạn giữ lại
# 4) A-roll (có thoại): cắt bỏ ngắt nghỉ, ầm à, nối liền 1 video, giữ độ phân giải gốc  5) B-roll: cắt không nén lại (giữ nguyên chất lượng)
import os, sys, json, time, re, subprocess, base64, glob, shutil, hashlib, urllib.request, urllib.error, urllib.parse, unicodedata, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

API, SEC = os.environ['MICC_API'], os.environ['MICC_SECRET']
SITE = os.environ.get('MICC_SITE', 'https://miccmedia.edgeone.dev').rstrip('/')
ROOT = os.environ.get('MICC_ROOT', '1-26OvV9W2MuApRRgK43URqgiC-b07MfV')
T0, MAXMIN = time.time(), float(os.environ.get('MAX_MIN', '330'))
TMP = os.environ.get('LOC_TMP', '/tmp/loc')
WM = os.environ.get('LOC_WHISPER', 'small')
SETTLE, FAIL_WAIT, FAIL_MAX = 8 * 60, 20 * 60, 3
LOC_V = '2'  # đổi số này = mọi buổi quay AI đã lọc bằng bản cũ sẽ được lọc lại (bản cũ cho vào thùng rác)
SCRIPT_ID = os.environ.get('MICC_SCRIPT_ID', '1FnCDqrEoF31eZxvasYTjs9yfCpu5a6lhhJiv2rU7kRALq86nFBzTISOD')
TMPNAME = '_AI đang lọc…'
FOLDER = 'application/vnd.google-apps.folder'
G = 'https://www.googleapis.com'
GEM = 'https://generativelanguage.googleapis.com/v1beta/'
ZALO = 'https://bot-api.zaloplatforms.com/bot'
AP = {'ailoc': '1'}  # dấu nhận file / thư mục AI lọc (bản 254: KHÔNG gắn người sở hữu – chủ yêu cầu để trống)
mine_ap = lambda ap: (ap or {}).get('ailoc') == '1' or (ap or {}).get('by') == 'ai-loc'
FILL = {'ừ', 'ừm', 'ờ', 'ờm', 'ơ', 'à', 'ầm', 'ậm', 'hừm', 'ừa', 'um', 'uhm', 'uh', 'ah', 'eh', 'hmm', 'ưm', 'ừ ừ', 'ơ ơ'}
VN = datetime.timezone(datetime.timedelta(hours=7))
FIELDS = 'id,name,mimeType,size,createdTime,thumbnailLink,appProperties,parents,shortcutDetails,videoMediaMetadata(width,height,durationMillis),imageMediaMetadata(width,height,rotation)'  # giống máy chủ (để báo thẳng vào kho web)

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
            if i == 3 or 'AUTH' in str(e): raise
            log('  máy chủ lỗi, thử lại:', e); time.sleep(3 * (i + 1))

TK = {'v': None, 't': 0}
def tok():
    if time.time() - TK['t'] > 1500: TK['v'] = api('pxToken')['token']; TK['t'] = time.time()
    return TK['v']
def drive(path, data=None, method=None, params='supportsAllDrives=true'):
    if isinstance(params, dict): params = urllib.parse.urlencode(dict({'supportsAllDrives': 'true'}, **params))
    for i in range(5):
        try: return http(G + '/drive/v3/' + path + ('?' + params if params else ''), data, {'Authorization': 'Bearer ' + tok()}, method)
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429: raise RuntimeError('Drive %s: %s' % (e.code, e.read()[:200]))
            time.sleep(2 * (i + 1))
    raise RuntimeError('Drive không phản hồi')
def durl(fid): return G + '/drive/v3/files/' + fid + '?alt=media&supportsAllDrives=true'
# TẢI KIỂU KHÁCH (chủ dặn 11/11): thư mục PHÒNG TRUYỀN THÔNG MICC đã công khai → tải không đăng nhập, KHÔNG tính vào hạn mức tải của tài khoản MICC
# (Drive trên máy người dùng / CapCut không bị chặn lây). File nào không tải khách được thì mới dùng tài khoản.
_ANON = {}
def aurl(fid): return 'https://drive.usercontent.google.com/download?id=%s&export=download&confirm=t' % fid
def anon_ok(fid):
    if fid not in _ANON:
        try:
            req = urllib.request.Request(aurl(fid), headers={'Range': 'bytes=0-1023'})
            with urllib.request.urlopen(req, timeout=30) as r: _ANON[fid] = r.status in (200, 206) and 'text/html' not in (r.headers.get('Content-Type') or '')
        except Exception: _ANON[fid] = False
    return _ANON[fid]
def fin(fid, ss=None, t=None):
    a = ['-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5']
    if ss is not None: a += ['-ss', '%.3f' % ss]
    if t is not None: a += ['-t', '%.3f' % t]
    if anon_ok(fid): return a + ['-i', aurl(fid)]
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
            req = urllib.request.Request(aurl(fid), headers={'Range': 'bytes=%d-' % got}) if anon_ok(fid) else urllib.request.Request(durl(fid), headers={'Authorization': 'Bearer ' + tok(), 'Range': 'bytes=%d-' % got})
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
    import numpy as np; from PIL import Image
    im = Image.open(path).convert('L'); im.thumbnail((256, 256)); return np.asarray(im, dtype=np.float32)
def lap(a):
    import numpy as np
    return float(np.var(4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]))
def shift(a, b):
    import numpy as np
    if a.shape != b.shape: return 0.0
    F = np.fft.fft2(a - a.mean()) * np.conj(np.fft.fft2(b - b.mean())); F /= np.abs(F) + 1e-6
    c = np.abs(np.fft.ifft2(F)); y, x = np.unravel_index(np.argmax(c), c.shape); h, w = a.shape
    y = y - h if y > h // 2 else y; x = x - w if x > w // 2 else x
    return float(np.hypot(x, y)) / w
def analyze(i, v):
    from PIL import Image
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
    return dict(i=i, name=v['name'], sub=v.get('dir', ''), id=v['id'], size=v.get('size') or 0, dur=dur, w=vs.get('width'), h=vs.get('height'), codec=vs.get('codec_name'),
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
    import numpy as np
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
    return 'VIDEO #%d · %stên "%s" · %.1f giây · %sx%s · độ nét TB %.0f · chất lượng hình: %s\nLời thoại: %s' % (a['i'], ('thư mục con “%s” · ' % a['sub']) if a.get('sub') else '', a['name'], a['dur'], a['w'], a['h'], ref, q, tx[:3500] or '(không có lời)')

# ---------- 3) Gemini lên kế hoạch lọc ----------
SYS = '''Bạn là video editor chuyên nghiệp của team truyền thông bất động sản MICC. Bạn nhận toàn bộ source (cảnh quay gốc) của 1 buổi quay: ảnh khung hình, chất lượng hình, lời thoại có mốc thời gian (lời do máy nghe, có thể sai chính tả).
Nhiệm vụ: LỌC SOURCE như editor lọc tay trước khi dựng.
1. Hiểu buổi quay nhằm mục đích gì. Nếu video đã được xếp vào các thư mục con (vd “Kịch bản 1”, “Kịch bản 2”) thì mỗi thư mục con thường là 1 kịch bản – dùng làm gợi ý chính (tên kịch bản vẫn đặt theo nội dung thật). Một buổi quay có thể quay NHIỀU KỊCH BẢN khác nhau: phân biệt dựa vào nội dung lời thoại, B-roll hợp với lời thoại nào, bối cảnh, nhân vật, trang phục. Đặt tên từng kịch bản ngắn gọn (vd "Giới thiệu ứng dụng NextMe", "Dự án Vinhomes Ocean Park đang mở bán").
2. Phân loại: A-roll = cảnh có người nói theo kịch bản (MC, phỏng vấn, thuyết trình); B-roll = cảnh minh họa không thoại chính (toàn cảnh, cận cảnh, chi tiết, flycam, quay màn hình…).
3. Cảnh quay lại nhiều lần (cùng góc / cùng nội dung / cùng câu thoại): chỉ chọn 1 bản tốt nhất – nét, ổn định, bố cục đẹp, nói trôi chảy, ĐỦ Ý nhất. Bỏ hẳn bản kém, bản hỏng, bản quay nhầm.
4. Với mỗi video được chọn, ghi các đoạn GIỮ LẠI (giây, theo video gốc). A-roll: giữ TRỌN câu nói, tuyệt đối không cắt giữa câu, giữ từ đầu câu đầu tới hết câu cuối của phần nói đúng; chỉ bỏ phần nói hỏng rồi nói lại (giữ lần nói đúng cuối cùng), nói linh tinh ngoài kịch bản, đoạn chuẩn bị / chờ. B-roll: giữ đoạn đẹp, ổn định (bỏ rung lắc, mờ, lia vội); nhiều đoạn đẹp khác nhau thì giữ nhiều đoạn.
5. Mỗi video gốc dùng tối đa 1 lần. Thứ tự trong từng kịch bản: A-roll theo đúng mạch kịch bản; B-roll theo mạch hình ảnh hợp lý.
6. "noi_dung": nếu clip có lời thoại thì ghi LỜI THOẠI của phần giữ lại (sửa đúng chính tả tiếng Việt, giữ nguyên ý người nói, nếu dài thì lấy câu đầu, tối đa 90 ký tự); nếu không có lời thoại thì mô tả tóm tắt hình ảnh (tối đa 60 ký tự, vd "Toàn cảnh hồ bơi lúc hoàng hôn").
Trả về JSON đúng dạng: {"muc_dich":"1 câu mục đích buổi quay","kich_ban":[{"so":1,"ten":"..."}],"clips":[{"kb":<số kịch bản>,"loai":"A"|"B","video":<số #>,"giu":[[giây_bắt_đầu,giây_kết_thúc],...],"noi_dung":"..."}]}'''

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
        tx = ' '.join(s['t'] for s in a['segs'])[:90]
        cl.append({'kb': 1, 'loai': 'A' if sp >= 8 else 'B', 'video': a['i'], 'giu': [[0, a['dur']]] if sp >= 8 else [[s0, min(e0, a['dur'])]], 'noi_dung': tx if sp >= 8 else 'Cảnh minh họa'})
    return {'muc_dich': '', 'kich_ban': [{'so': 1, 'ten': ''}], 'clips': sorted(cl, key=lambda c: c['loai'])}

# ---------- 4) cắt ghép ----------
def norm(w): return re.sub(r'[^\w\s]', '', unicodedata.normalize('NFC', w.lower())).strip()
FR = .02  # 20 ms / khung
def vad(a):  # True = có tiếng người nói (theo năng lượng âm thanh, khoảng hở < 0,25 s coi như vẫn đang nói)
    if 'vad' in a: return a['vad']
    a['vad'] = None
    if not a.get('wav') or not os.path.exists(a['wav']): return None
    import numpy as np, wave
    with wave.open(a['wav']) as w: x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    F = int(16000 * FR); m = len(x) // F
    if m < 10: return None
    e = 10 * np.log10((x[:m * F].reshape(m, F) ** 2).mean(1) + 1)
    lo, hi = np.percentile(e, 15), np.percentile(e, 97)
    thr = max(lo + 9, hi - 30) if hi - lo > 15 else lo + 6
    v = e > thr; k = int(.25 / FR)
    idx = np.where(v)[0]
    for p, q in zip(idx[:-1], idx[1:]):
        if 1 < q - p <= k: v[p:q] = True
    a['vad'] = v; return v
def sp(a, t):
    v = a['vad']; i = int(t / FR)
    return bool(v[i]) if v is not None and 0 <= i < len(v) else False
def speech_cut(a, keep):
    dur = a['dur']; v = vad(a)
    if v is None: return [[max(0, keep[0][0] - 2), min(dur, keep[-1][1] + 2)]] if len(keep) == 1 else [list(k) for k in keep]
    segs = a.get('segs') or []
    R = []
    for s, e in keep:
        for g in segs:  # bám theo câu (máy nghe): không bắt đầu / kết thúc giữa câu
            if g['s'] < s < g['e']: s = g['s']
            if g['s'] < e < g['e']: e = g['e']
        n = 0
        while s > 0 and sp(a, s - FR) and n < 150: s -= FR; n += 1  # còn đang nói → lùi tới chỗ lặng
        n = 0
        while e < dur and sp(a, e) and n < 250: e += FR; n += 1      # còn đang nói → cho nói hết
        R.append([max(0, s), min(dur, e)])
    R.sort(); M = []
    for s, e in R:
        if M and s <= M[-1][1] + .3: M[-1][1] = max(M[-1][1], e)
        else: M.append([s, e])
    out = []
    fill = [w for g in segs for w in g['w'] if norm(w[2]) in FILL and w[1] - w[0] < 1.2]
    for k, (s, e) in enumerate(M):
        s0 = s - (.35 if k else 0); e0 = e + (.45 if k < len(M) - 1 else 0)
        if k == 0:  # mở đầu: thêm tối đa 2 s trước câu đầu (dừng lại nếu gặp tiếng nói khác)
            t = s
            while t > 0 and s - t < 2 and not sp(a, t - FR): t -= FR
            s0 = t + (.15 if t > 0 and sp(a, t - FR) else 0)
        if k == len(M) - 1:  # kết thúc: thêm tối đa 2 s sau câu cuối
            t = e
            while t < dur and t - e < 2 and not sp(a, t): t += FR
            e0 = t - (.15 if t < dur and sp(a, t) else 0)
        s0, e0 = max(0, s0), min(dur, e0)
        # bên trong: bỏ khoảng lặng dài ≥ 1,2 s (chừa 0,4 s mỗi bên) và tiếng ầm à đứng riêng (có lặng 2 bên)
        cuts, t, st = [], s, None
        while t < e:
            if not sp(a, t):
                st = t if st is None else st
            else:
                if st is not None and t - st >= 1.2: cuts.append([st + .4, t - .4])
                st = None
            t += FR
        for w in fill:
            if s + .5 < w[0] and w[1] < e - .5 and not sp(a, w[0] - .3) and not sp(a, w[1] + .3): cuts.append([w[0] - .08, w[1] + .08])
        cuts.sort(); cur = s0
        for c0, c1 in cuts:
            if c0 > cur + .3: out.append([cur, c0])
            cur = max(cur, c1)
        if e0 > cur + .2: out.append([cur, e0])
    return out

def safe(n, k=150): return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', str(n))).strip()[:k].strip() or 'Cảnh'
def short(t, k):
    t = safe(t, 400)
    if len(t) <= k: return t
    t = t[:k].rsplit(' ', 1)[0]; return t.rstrip(',.;:') + '...'  # bản 263.34 (chủ báo): không dùng ký tự “…” trong tên file lọc – CapCut trên Windows không liên kết được file

def copy_cut(a, s, e, src, out):  # 1 đoạn liền: cắt không nén lại (giữ nguyên chất lượng gốc) chỉ khi điểm đầu đúng khung chính (bản 262: chặt hơn để không đen / đứng hình đầu)
    ks = max([t for t in a['kt'] if t <= s + .02] or [-99])
    if s - ks > .25: return False
    run(['ffmpeg', '-y', '-v', 'error', '-ss', '%.3f' % max(0, ks), '-i', src, '-t', '%.3f' % (e - max(0, ks)), '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy', '-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', out], timeout=1800)
    return True

def make_a(a, segs, src, out):  # nối các đoạn giữ lại thành 1 video (concat demuxer: mở từng đoạn lần lượt, không tốn RAM)
    lst = out + '.txt'; q = src.replace("'", "'\\''")
    open(lst, 'w').write(''.join("file '%s'\ninpoint %.3f\noutpoint %.3f\n" % (q, s, e) for s, e in segs))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'format=yuv420p',
           '-c:v', 'libx264', '-preset', os.environ.get('LOC_PRESET', 'ultrafast'), '-crf', os.environ.get('LOC_CRF', '14'),
           '-af', 'aresample=async=1:first_pts=0', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-threads', '0', out]
    run(cmd, timeout=5400); os.remove(lst)

# bản 262 (chủ dặn): cắt CHÍNH XÁC từng đoạn (tua chính xác tới khung, nén lại) rồi nối – không còn đen / đứng hình đầu video, hình tiếng không lệch, không mất câu cuối
def render_exact(a, segs, src, out):
    P, C = os.environ.get('LOC_PRESET', 'ultrafast'), os.environ.get('LOC_CRF', '14'); parts = []
    for k, (s0, e0) in enumerate(segs):
        pth = out + '.x%02d.mp4' % k
        run(['ffmpeg', '-y', '-v', 'error', '-ss', '%.3f' % s0, '-i', src, '-t', '%.3f' % (e0 - s0), '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', P, '-crf', C,
             '-af', 'aresample=async=1000', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2', '-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', '-threads', '0', pth], timeout=5400)
        parts.append(pth)
    if len(parts) == 1: os.replace(parts[0], out); return
    lst = out + '.txt'; open(lst, 'w').write(''.join("file '%s'\n" % x.replace("'", "'\\''") for x in parts))
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', out], timeout=3600)
    for x in parts + [lst]: os.remove(x)

def qa(path, aroll=True, full=True, want=None):  # tự kiểm tra file lọc: đen màn / đứng hình (đầu hoặc giữa), hình – tiếng lệch, cắt giữa câu ở cuối
    import numpy as np
    issues = {}
    pr = json.loads(run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format'] + (path if isinstance(path, list) else [path]), timeout=180).stdout or '{}')
    dv = [float(x.get('duration') or 0) for x in pr.get('streams', []) if x.get('codec_type') == 'video']; da = [float(x.get('duration') or 0) for x in pr.get('streams', []) if x.get('codec_type') == 'audio']
    D = float((pr.get('format') or {}).get('duration') or (dv[0] if dv else 0))
    if dv and da and dv[0] and da[0] and abs(dv[0] - da[0]) > .6: issues['lech'] = round(dv[0] - da[0], 2)
    if want and D and abs(D - want) > max(.8, want * .04): issues['dai_sai'] = round(D - want, 2)  # dài / ngắn hơn phần cần giữ (vd dính phần trước điểm cắt)
    src = path if isinstance(path, list) else ['-i', path]
    p = subprocess.run(['ffmpeg', '-v', 'info'] + (src if full else src[:-2] + ['-t', '14'] + src[-2:]) + ['-map', '0:v:0', '-vf', 'scale=320:-2,blackdetect=d=0.5:pix_th=0.08,freezedetect=n=-60dB:d=1', '-f', 'null', '-'], capture_output=True, text=True, timeout=3600)
    for m in re.finditer(r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)', p.stderr):
        b0, b1, bd = map(float, m.groups())
        if b0 < .4 and bd >= .6: issues['den_dau'] = round(b1, 2)
        elif bd >= 2 and b1 < D - .3: issues.setdefault('den_giua', round(b0, 2))
    fz = re.findall(r'freeze_start: ([\d.]+)', p.stderr); fe = re.findall(r'freeze_end: ([\d.]+)', p.stderr)
    for k, f0 in enumerate(fz):
        f0 = float(f0); f1 = float(fe[k]) if k < len(fe) else D
        if f0 < .4 and f1 - f0 >= 1.0 and aroll: issues['dung_dau'] = round(f1, 2)  # B-roll đặt máy cố định có thể đứng yên thật
        elif aroll and f1 - f0 >= 3 and f1 < D - .3: issues.setdefault('dung_giua', round(f0, 2))
    if aroll and da:  # tiếng 0,25 s cuối còn to như đang nói → cắt giữa câu
        q = subprocess.run(['ffmpeg', '-v', 'error'] + (['-sseof', '-6'] if not full else []) + src + ['-map', '0:a:0', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, timeout=1800).stdout
        x = np.frombuffer(q, dtype=np.int16).astype(np.float32)
        F = 320; m = len(x) // F
        if m > 40:
            e = 10 * np.log10((x[:m * F].reshape(m, F) ** 2).mean(1) + 1); thr = max(np.percentile(e, 90) - 10, 40)
            if (e[-12:] > thr).mean() > .5: issues['cat_cuoi'] = 1
    return issues

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

def upload(path, name, parent, extra=None):
    size = os.path.getsize(path)
    mt = 'video/quicktime' if path.lower().endswith('.mov') else 'video/mp4'
    for i in range(5):
        try:
            r, _ = http(G + '/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=' + urllib.parse.quote(FIELDS), {'name': name, 'parents': [parent], 'appProperties': dict(AP, **(extra or {}))},
                        {'Authorization': 'Bearer ' + tok(), 'X-Upload-Content-Type': mt, 'X-Upload-Content-Length': str(size)}, raw=True)
            url = r.headers['Location']; pos = 0
            with open(path, 'rb') as f:
                while True:
                    f.seek(pos); b = f.read(64 << 20)
                    req = urllib.request.Request(url, data=b, method='PUT', headers={'Content-Range': 'bytes %d-%d/%d' % (pos, pos + len(b) - 1, size) if size else 'bytes */0'})
                    try:
                        with urllib.request.urlopen(req, timeout=600) as rr: return json.loads(rr.read())
                    except urllib.error.HTTPError as e:
                        if e.code != 308: raise
                        rg = e.headers.get('Range'); pos = int(rg.split('-')[1]) + 1 if rg else pos + len(b)
        except Exception as e:
            log('  tải lên lỗi, thử lại:', e); time.sleep(4 * (i + 1))
    raise RuntimeError('không tải được “%s” lên Drive' % name)

# ---------- cấu hình: khóa Gemini / Zalo từ gói máy chủ mã hóa trên web ----------
CFG = {}
def cfg():
    if CFG: return CFG
    enc = urllib.request.urlopen(SITE + '/cg.bin?t=%d' % time.time(), timeout=120).read()
    k = hashlib.sha256(('micc-cg|' + SEC).encode()).digest(); out = bytearray(len(enc))
    for b in range((len(enc) + 31) // 32):
        ks = hashlib.sha256(k + b.to_bytes(4, 'big')).digest()
        for i in range(32):
            p = b * 32 + i
            if p < len(enc): out[p] = enc[p] ^ ks[i]
    src = out.decode('utf-8', 'replace')
    g = lambda n: (re.search(n + r"\s*=\s*'([^']+)'", src) or [None, ''])[1]
    CFG.update(src=src, gem=g('GEMINI_API_KEY'), zalo=g('ZALO_BOT_TOKEN'), ver=(re.search(r"BOT_VER\s*=\s*'([^']+)'", src) or [None, ''])[1])
    if not CFG['gem']: log('  (không đọc được khóa Gemini từ web)')
    return CFG

def gem_models(key):
    try:
        j = http(GEM + 'models?pageSize=200', headers={'x-goog-api-key': key}, timeout=60)
        L = [m['name'].split('/')[-1] for m in j.get('models', []) if 'generateContent' in (m.get('supportedGenerationMethods') or [])]
        L = [n for n in L if re.match(r'^gemini-[\d.]+-flash(-lite)?$|^gemini-flash(-lite)?-latest$', n)]
        ver = lambda n: float((re.search(r'gemini-(\d+(?:\.\d+)?)', n) or [0, 0])[1] or 0)
        L.sort(key=lambda n: (-('latest' in n), -ver(n), 'lite' in n))
        if L: return L[:5]
    except Exception as e: log('  không lấy được danh sách mô hình Gemini:', e)
    return ['gemini-flash-latest', 'gemini-2.5-flash', 'gemini-flash-lite-latest']

def norm1(x):
    x = unicodedata.normalize('NFD', str(x or '').replace('đ', 'd').replace('Đ', 'd'))
    x = ''.join(c for c in x if not unicodedata.combining(c)).lower()
    return ' '.join(re.sub(r'[^a-z0-9\s]', ' ', x).split())
def ts(x):
    try: return datetime.datetime.fromisoformat(str(x).replace('Z', '+00:00')).timestamp()
    except Exception: return 0
VEXT = ('.mp4', '.mov', '.m4v', '.mxf', '.mts', '.m2ts', '.avi', '.mkv', '.mpg', '.mpeg', '.webm', '.3gp')
PROXY = ('.lrf', '.lrv', '.thm', '.ser')  # file xem trước độ phân giải thấp của DJI / GoPro – bỏ qua
def is_video(f):
    mt = f.get('mimeType') or ''
    if f.get('name', '').lower().endswith(PROXY): return False
    if mt == 'application/vnd.google-apps.shortcut': mt = (f.get('shortcutDetails') or {}).get('targetMimeType') or ''
    return mt.startswith('video/') or (not mt.startswith('application/vnd.google-apps') and f.get('name', '').lower().endswith(VEXT))

def listq(q, fields, extra=None):
    out, pt = [], None
    while True:
        prm = dict({'q': q, 'fields': 'nextPageToken,files(%s)' % fields, 'pageSize': 1000, 'includeItemsFromAllDrives': 'true'}, **(extra or {}))
        if pt: prm['pageToken'] = pt
        j = drive('files', params=prm); out += j.get('files', []); pt = j.get('nextPageToken')
        if not pt: return out

ROOTI = {}
def root_info():
    if not ROOTI: ROOTI.update(drive('files/' + ROOT, params={'fields': 'id,name,driveId,appProperties'}))
    return ROOTI
def corpora():
    d = root_info().get('driveId'); return {'corpora': 'drive', 'driveId': d} if d else {}

# ---------- tìm buổi quay cần lọc (đọc thẳng Drive, không cần máy chủ) ----------
def scan():
    # bản 263.40 (chủ dặn 10/11): KHÔNG tạo thư mục Lọc nữa – dựng thẳng từ source gốc. Máy lọc tắt hẳn.
    if os.environ.get('LOC_ON') != '1': log('máy lọc đã tắt (chủ dặn không tạo thư mục Lọc)'); return []
    now = time.time()
    fol = listq("mimeType='%s' and trashed=false" % FOLDER, 'id,name,parents,appProperties', corpora())
    by = {f['id']: f for f in fol}; memo = {ROOT: True}
    def under(fid, d=0):
        if fid in memo: return memo[fid]
        f = by.get(fid); r = bool(f and d < 40 and any(under(p, d + 1) for p in f.get('parents') or []))
        memo[fid] = r; return r
    isrc = lambda n: re.search(r'\bsources?\b', norm1(n)) is not None  # đúng chữ “source” (không nhận “Resources”)
    srcs = {f['id']: f for f in fol if isrc(f['name']) and under(f['id'])}
    for f in fol:  # dọn thư mục Lọc AI làm nhầm (buổi quay không nằm trong thư mục Source, hoặc nằm trong thư mục “Bộ nhớ đệm (không xóa)” – bản 262)
        ap = f.get('appProperties') or {}
        if mine_ap(ap) and (re.match(r'^loc\b', norm1(f['name'])) or f['name'] == TMPNAME):
            sh = by.get((f.get('parents') or [''])[0]) or {}
            def insrc(fid, g=0):  # thư mục Lọc nằm ở BẤT KỲ tầng nào bên trong 1 thư mục Source (bản 262: Lọc nằm ngay trong thư mục chứa video, có thể sâu hơn buổi quay)
                x = by.get(fid); return bool(x and g < 40 and any(p in srcs or insrc(p, g + 1) for p in x.get('parents') or []))
            if (sh.get('appProperties') or {}).get('mcache') == '1' or (re.match(r'^loc\b', norm1(f['name'])) and not insrc(f['id'])):
                try: drive('files/' + f['id'], {'trashed': True}, method='PATCH'); ix(dele=[f['id']]); log('  dọn thư mục Lọc làm nhầm trong', sh.get('name'))
                except Exception as e: log('  không dọn được:', e)
    # bản 262 (chủ dặn): thư mục “Lọc” luôn nằm NGAY TRONG thư mục chứa video. Mỗi thư mục có video (buổi quay hoặc thư mục con của nó, vd “Kịch bản 1”) = 1 lượt lọc riêng, chỉ lấy video nằm trực tiếp trong đó.
    FL = 'id,name,mimeType,size,createdTime,modifiedTime,appProperties,shortcutDetails,videoMediaMetadata'
    skipd = lambda c: re.match(r'^loc\b', norm1(c['name'])) or c['name'] == TMPNAME or mine_ap(c.get('appProperties')) or (c.get('appProperties') or {}).get('mcache') == '1'
    ready = []
    for f in fol:
        par = [p for p in f.get('parents') or [] if p in srcs]
        if not par or skipd(f): continue  # thư mục con của Source = buổi quay (kể cả tên có chữ source)
        nodes, st = [], [(f, f['name'], 0)]
        while st and len(nodes) < 80:
            d, path, dep = st.pop(0)
            ch = listq("'%s' in parents and trashed=false" % d['id'], FL, corpora())
            dirs = [c for c in ch if c['mimeType'] == FOLDER]
            locs = [c for c in dirs if re.match(r'^loc\b', norm1(c['name']))]
            mine = [c for c in locs if mine_ap(c.get('appProperties'))]
            nd = dict(f=d, path=path, vids=[c for c in ch if is_video(c)], locs=locs, mine=mine, tmp=[c for c in dirs if c['name'] == TMPNAME], kids=[])
            nodes.append(nd)
            for c in dirs:
                if not skipd(c) and dep < 4: nd['kids'].append(c['id']); st.append((c, path + ' › ' + c['name'], dep + 1))
        byn = {n['f']['id']: n for n in nodes}
        def hasv(n, g=0): return g < 8 and any(byn[k]['vids'] or hasv(byn[k], g + 1) for k in n['kids'] if k in byn)
        undone = 0
        for n in nodes:
            if not n['vids']: continue
            ap = n['f'].get('appProperties') or (by.get(n['f']['id']) or {}).get('appProperties') or {}
            done = ap.get('locDone') and ap.get('locV') == LOC_V and (ap.get('locL') == '1' or not hasv(n))  # bản cũ gộp cả thư mục con vào 1 thư mục Lọc → lọc lại đúng chỗ
            if done: continue
            undone += 1
            if len(n['locs']) > len(n['mine']): continue  # editor đã lọc tay (thư mục Lọc không phải của AI) → bỏ qua
            nf = int(ap.get('locFail') or 0) if ap.get('locV') == LOC_V else 0
            if nf >= FAIL_MAX or (nf and now - float(ap.get('locFailT') or 0) < FAIL_WAIT): continue
            last = max(max(ts(c.get('createdTime')), ts(c.get('modifiedTime'))) for c in n['vids'])
            if now - last < SETTLE: continue  # còn đang tải lên
            def vrow(c):
                sd = c.get('shortcutDetails') or {}; vm = c.get('videoMediaMetadata') or {}
                return {'id': sd.get('targetId') or c['id'], 'name': c['name'], 'dir': '', 'size': int(c.get('size') or 0), 'dur': (int(vm.get('durationMillis') or 0)) / 1000, 'w': vm.get('width'), 'h': vm.get('height')}
            nk = lambda c: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', c['name'])]
            ready.append({'fid': n['f']['id'], 'name': n['path'], 'src': srcs[par[0]]['name'], 'nfail': nf, 'last': last, 'stale': [c['id'] for c in n['mine'] + n['tmp']], 'videos': [vrow(c) for c in sorted(n['vids'], key=nk)]})
        if not undone:  # thư mục Lọc AI cũ nằm ở thư mục KHÔNG chứa video (vd ngoài “Kịch bản 1”, “Kịch bản 2”) → các thư mục con đã có Lọc riêng → bỏ bản cũ
            for n in nodes:
                if n['vids']: continue
                for c in n['mine'] + n['tmp']:
                    try: drive('files/' + c['id'], {'trashed': True}, method='PATCH'); ix(dele=[c['id']]); log('  bỏ thư mục Lọc cũ đặt sai chỗ trong', n['path'])
                    except Exception as e: log('  không bỏ được Lọc sai chỗ:', e)
    ready.sort(key=lambda j: -j['last'])  # buổi quay vừa tải lên làm trước
    return ready

def repair_lost():  # bản 262: khôi phục thư mục Lọc mới bị quy tắc dọn cũ cho nhầm vào thùng rác (Lọc đúng chỗ của thư mục chứa video: id = locOut của thư mục đó)
    if os.environ.get('LOC_ON') != '1': return  # bản 263.40: máy lọc tắt – KHÔNG khôi phục thư mục Lọc chủ đã xóa
    try: L = listq("trashed=true and mimeType='%s' and name='Lọc' and appProperties has { key='ailoc' and value='1' }" % FOLDER, 'id,name,parents,modifiedTime', corpora())
    except Exception as e: log('  không rà được thư mục Lọc trong thùng rác:', e); return
    for f in L:
        par = (f.get('parents') or [''])[0]
        try: pa = drive('files/' + par, params='supportsAllDrives=true&fields=id,name,trashed,appProperties')
        except Exception: continue
        pap = pa.get('appProperties') or {}
        if not pa.get('trashed') and pap.get('locOut') == f['id'] and pap.get('locL') == '1' and pap.get('mcache') != '1':  # chỉ Lọc của cách xếp mới (ngay trong thư mục chứa video); Lọc cũ sai chỗ / trong bộ nhớ đệm thì thôi
            try: uf = drive('files/' + f['id'], {'trashed': False}, method='PATCH', params='supportsAllDrives=true&fields=' + urllib.parse.quote(FIELDS)); ix([uf]); log('  ✓ khôi phục thư mục Lọc trong', pa.get('name'))
            except Exception as e: log('  không khôi phục được:', e)

def fix_old():  # bản 254: file / thư mục AI lọc cũ → bỏ người sở hữu “AI lọc source”, đổi tên “A01 - tên gốc - nội dung” → “A01 - nội dung - tên gốc”
    try: L = listq("trashed=false and appProperties has { key='by' and value='ai-loc' }", 'id,name,mimeType', corpora())
    except Exception as e: log('  không rà được file AI lọc cũ:', e); return
    if not L: return
    log('Rà soát %d file / thư mục AI lọc cũ' % len(L)); out = []
    for f in L:
        b = {'appProperties': {'by': None, 'byName': None, 'via': None, 'ailoc': '1'}}
        m = re.match(r'^([AB]\d{2}) - (.+?) - (.+?)(\.[A-Za-z0-9]{2,5})?$', f['name']) if f['mimeType'] != FOLDER else None
        if m: b['name'] = '%s - %s - %s%s' % (m.group(1), m.group(3), m.group(2), m.group(4) or '')
        try: out.append(drive('files/' + f['id'], b, method='PATCH', params={'fields': FIELDS}))
        except Exception as e: log('  không sửa được', f['name'], e)
    for i in range(0, len(out), 50): ix(out[i:i + 50])
    log('  ✓ đã bỏ người sở hữu + đổi tên %d mục' % len(out))

def mark(fid, **kv): drive('files/' + fid, {'appProperties': {k: (None if v is None else str(v)[:100]) for k, v in kv.items()}}, method='PATCH')

# ---------- báo nhóm test Zalo (tự gửi, không qua máy chủ) ----------
ZG = {}
def zcfg():  # nhóm Zalo: zn = nhóm thông báo (+ test), zt = nhóm test; máy chủ không trả lời thì dùng danh sách đã lưu trên thư mục kho
    if ZG.get('t', 0) > time.time() - 600: return ZG
    ap = root_info().get('appProperties') or {}; zn, zt = [], []
    try:
        j = api('locCfg'); zn = [str(x) for x in (j.get('zn') or [])]; zt = [str(x) for x in (j.get('zt') or [])]
        up = {}
        if zn and ','.join(zn)[:110] != (ap.get('locZN') or ''): up['locZN'] = ','.join(zn)[:110]
        if zt and ','.join(zt)[:110] != (ap.get('locZT') or ''): up['locZT'] = ','.join(zt)[:110]
        if up: mark(ROOT, **up); ap.update(up)
    except Exception as e: log('  (máy chủ chưa trả danh sách nhóm: %s)' % str(e)[:80])
    sp = lambda k: [x for x in (ap.get(k) or '').split(',') if x]
    ZG.update(t=time.time(), zn=zn or sp('locZN'), zt=zt or sp('locZT')); return ZG
def groups():  # tin XONG: bản 263.38 (chủ dặn) – việc AI làm chỉ báo nhóm test, không báo nhóm thông báo
    g = zcfg(); return list(dict.fromkeys(g['zt']))
SAID = set()
def tsay(text, once=None):  # báo NGAY vào nhóm test: bắt đầu lọc, lỗi, hết việc (chủ yêu cầu 08/11)
    if once:
        if once in SAID: return
        SAID.add(once)
    log('  [Zalo test]', text.replace('\n', ' | ')[:160])
    for g in zcfg()['zt']:
        try: zsend(g, text)
        except Exception as e: log('  Zalo test lỗi:', str(e)[:100])
def ix(files=None, dele=None, link=None):  # báo máy chủ đưa ngay vào kho web (không tốn hạn mức gọi mạng của máy chủ)
    b = {'files': files or []}
    if dele: b['del'] = dele
    if link: b['link'] = link
    try: return api('locIx', **b)
    except Exception as e: log('  (chưa báo được kho web: %s)' % str(e)[:80]); return {}
def zsend(chat, text, photo=None):
    tk = cfg()['zalo']
    if photo:  # tin kèm ảnh (ảnh ghép các file lọc)
        try:
            j = http(ZALO + tk + '/sendPhoto', {'chat_id': chat, 'photo': photo, 'caption': text[:1900]}, timeout=90)
            if j.get('ok') is not False: return True
        except Exception as e: log('  Zalo ảnh lỗi:', str(e).replace(tk, '***')[:160])
    for i in range(3):
        try:
            j = http(ZALO + tk + '/sendMessage', {'chat_id': chat, 'text': text[:1900]}, timeout=60)
            if j.get('ok') is not False: return True
        except Exception as e: log('  Zalo lỗi:', str(e).replace(tk, '***')[:160])
        time.sleep(3)
    return False
def flush_reports():  # báo các thư mục Lọc đã xong mà chưa báo được (vd. lúc chưa có mã nhóm)
    try: pend = listq("mimeType='%s' and trashed=false and appProperties has { key='locRep' and value='0' }" % FOLDER, 'id,name,description,appProperties', corpora())
    except Exception as e: log('  không đọc được tin chờ gửi:', e); return 0
    if not pend: return 0
    zt = groups()
    if not zt: log('  %d tin chờ gửi – chưa có mã nhóm test, gửi sau' % len(pend)); return len(pend)
    for f in pend:
        txt = f.get('description') or ''
        ap = f.get('appProperties') or {}; ids = [x for k in range(1, 7) for x in (ap.get('locI%d' % k) or '').split('.') if x]
        photo = (SITE + ('/xg/' + '.'.join(ids[:16]) if len(ids) > 1 else '/xt/' + ids[0] + '?w=480')) if ids else None  # luôn 1 ảnh (ghép tới 16 file lọc)
        if txt and all(zsend(g, txt, photo) for g in zt): mark(f['id'], locRep='1'); log('  ✓ đã báo nhóm Zalo:', txt.split('\n')[1][:80] if '\n' in txt else '')
    return 0

def prog(fid, txt):  # tiến độ hiện trong mô tả thư mục “_AI đang lọc…” (xem được ngay trên Drive)
    try: drive('files/' + fid, {'description': hm(time.time()) + ' · ' + txt}, method='PATCH'); log('  …', txt)
    except Exception: pass

def hm(t): return datetime.datetime.fromtimestamp(t, VN).strftime('%H:%M %d/%m')

# ---------- 1 buổi quay ----------
QA_N = {'den_dau': 'đen màn đầu video', 'den_giua': 'đen màn giữa video', 'dung_dau': 'đứng hình đầu video', 'dung_giua': 'đứng hình giữa video', 'lech': 'hình và tiếng lệch nhau', 'dai_sai': 'thời lượng sai (dính phần ngoài đoạn cắt)', 'cat_cuoi': 'cắt giữa câu ở cuối'}
def qa_txt(q): return ', '.join(QA_N.get(k, k) for k in q)
def meta(c):  # nguồn + mốc cắt lưu trong file lọc → sau này phát hiện lỗi thì làm lại đúng file đó
    sg = ';'.join('%.2f-%.2f' % (x, y) for x, y in c['segs']); m = {'locSrc': c['a']['id'], 'locT': c['t'], 'locQa': '1'}
    for k in range(4): m['locSg%d' % (k + 1)] = sg[k * 95:(k + 1) * 95] or None
    return {k: v for k, v in m.items() if v}
def ext_end(a, e):  # còn đang nói ở điểm cắt cuối → cho nói hết (tối đa thêm 4 giây) + 0,35 s đệm
    v = vad(a); dur = a['dur']
    if v is None: return min(dur, e + 1.5)
    t, n = e, 0
    while t < dur and n < 200 and (sp(a, t) or sp(a, t + .1) or sp(a, t + .2)): t += FR; n += 1
    return min(dur, t + .35)
def build(a, c, out):  # cắt → tự kiểm tra → sửa (tối đa 3 lần): đen / đứng hình đầu → cắt chính xác, nếu do chính video gốc thì bỏ phần đó; cắt giữa câu → kéo dài tới hết câu
    segs = [list(x) for x in c['segs']]; aroll = c['t'] == 'A' or bool(a['segs']); exact = False; last = {}
    for rnd in range(4):
        if not exact and len(segs) == 1 and copy_cut(a, segs[0][0], segs[0][1], c['src'], out): pass
        elif not exact and not aroll: make_b(a, segs, c['src'], out)
        else: render_exact(a, segs, c['src'], out); exact = True
        q = qa(out, aroll, want=sum(y - x for x, y in segs) if exact else None)
        if 'cat_cuoi' in q:  # đối chiếu lời thoại máy nghe: chỉ là lỗi khi điểm cắt cuối rơi giữa 1 từ / giữa câu; video gốc tự dừng giữa câu thì không kéo thêm được; tiếng ồn nền to không phải lỗi
            e = segs[-1][1]; W = [w for g in (a.get('segs') or []) for w in g.get('w') or []]
            mid = any(w[0] < e - .05 and w[1] > e + .05 for w in W) or (any(e - .3 < w[1] <= e + .05 for w in W) and any(e < w[0] < e + .3 for w in W))
            if e >= a['dur'] - .3 or (W and not mid): q.pop('cat_cuoi')
        if not q: c['segs'] = segs; return {}
        log('  ⚠ tự kiểm tra %s: %s → làm lại' % (c['nm'], qa_txt(q))); last = q
        if not exact: exact = True; continue  # lần đầu: chỉ cần cắt chính xác (lỗi do cắt nhanh không nén)
        ch = False
        if 'den_dau' in q or 'dung_dau' in q:  # vẫn đen / đứng hình dù cắt chính xác → do video gốc: bỏ phần đó
            cut = max(q.get('den_dau', 0), q.get('dung_dau', 0)) + .05
            if segs[0][1] - segs[0][0] > cut + .8: segs[0][0] += cut; ch = True
        if 'cat_cuoi' in q:
            e2 = ext_end(a, segs[-1][1])
            if e2 > segs[-1][1] + .05: segs[-1][1] = e2; ch = True
        if not ch: break
    c['segs'] = segs; return last

def job(jb, key, models):
    t0 = time.time(); vids = jb['videos']; title = (jb.get('src') or '') + ' › ' + jb['name']
    log('▶ Lọc', title, '·', len(vids), 'video · tải xong lúc', hm(jb['last']))
    tsay('🔄 AI BẮT ĐẦU LỌC SOURCE\n📁 %s\n🎬 %d video (video cuối tải lên %s)%s\n⏳ Còn %d buổi quay chờ sau buổi này' % (title, len(vids), hm(jb['last']), ' · lần thử %d' % (jb['nfail'] + 1) if jb.get('nfail') else '', jb.get('left', 0)))
    for x in jb.get('stale') or []:
        try: drive('files/' + x, {'trashed': True}, method='PATCH'); log('  bản lọc cũ → thùng rác')
        except Exception as e: log('  không bỏ được bản cũ:', e)
    if jb.get('stale'): ix(dele=jb['stale'])
    lf = drive('files', {'name': 'Lọc', 'mimeType': FOLDER, 'parents': [jb['fid']], 'appProperties': dict(AP, locRun='1'), 'description': 'AI đang lọc…'}, params={'fields': FIELDS}); loc = lf['id']; ix([lf])
    outs = []
    up = ThreadPoolExecutor(1); ups = []
    try:
        shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
        res = {}
        with ThreadPoolExecutor(4) as ex:
            fs = {ex.submit(analyze, i + 1, v): i + 1 for i, v in enumerate(vids)}
            for f in as_completed(fs):
                try: a = f.result()
                except Exception as e: log('  bỏ qua video #%d: %s' % (fs[f], e)); tsay('⚠️ AI lọc: không đọc được 1 video, bỏ qua\n📁 %s\n🎬 %s\n%s' % (title, vids[fs[f] - 1]['name'], str(e)[:200])); continue
                a['segs'] = transcribe(a['wav']); res[a['i']] = a
                log('  ✓ đã xem + nghe #%d %s (%.0fs, %d câu)' % (a['i'], a['name'], a['dur'], len(a['segs'])))
                if len(res) % 10 == 0: prog(loc, 'Đã xem + nghe %d / %d video' % (len(res), len(vids)))
        A = [res[k] for k in sorted(res)]
        if not A: raise RuntimeError('không đọc được video nào')
        log('  xem + nghe xong sau %.1f phút' % ((time.time() - t0) / 60))
        try: plan = gemini(key, models, {'title': title, 'vids': A}) if key else fallback(A)
        except Exception as e: log('  ', e, '→ dùng cách lọc đơn giản'); plan = fallback(A); tsay('⚠️ AI lọc: Gemini không trả kế hoạch, dùng cách lọc đơn giản (chỉ chia A-roll / B-roll, ít cắt)\n📁 %s\n%s' % (title, str(e)[:200]))
        kbs = {}
        for x in plan.get('kich_ban') or []:
            try: kbs[int(x.get('so'))] = safe(x.get('ten') or '', 80)
            except Exception: pass
        by = {a['i']: a for a in A}; seen = set(); clips = []
        for c in plan.get('clips') or []:
            try: vi = int(c.get('video'))
            except Exception: continue
            if vi not in by or vi in seen: continue
            a = by[vi]; keep = []
            for r in c.get('giu') or [[0, a['dur']]]:
                try: s0, e0 = max(0.0, float(r[0])), min(a['dur'], float(r[1]))
                except Exception: continue
                if e0 - s0 >= .8: keep.append([s0, e0])
            if not keep: continue
            try: kb = int(c.get('kb') or 1)
            except Exception: kb = 1
            seen.add(vi); clips.append(dict(t='A' if str(c.get('loai', 'B')).upper().startswith('A') else 'B', a=a, keep=sorted(keep), kb=kb if kb in kbs else (min(kbs) if kbs else 1),
                                            txt=str(c.get('noi_dung') or c.get('ten') or ' '.join(g['t'] for g in a['segs']) or 'Cảnh')))
        if not clips: raise RuntimeError('kế hoạch lọc không có file nào')
        used = sorted({c['kb'] for c in clips}); fold = {}
        if len(used) > 1:  # nhiều kịch bản → mỗi kịch bản 1 thư mục “1. Tên kịch bản”
            for n, kb in enumerate(used, 1):
                ff = drive('files', {'name': '%d. %s' % (n, kbs.get(kb) or 'Kịch bản %d' % n), 'mimeType': FOLDER, 'parents': [loc], 'appProperties': AP}, params={'fields': FIELDS}); fold[kb] = ff['id']; ix([ff])
        prog(loc, 'Đã xem hết %d video, AI chọn %d cảnh%s – đang cắt ghép, xong file nào hiện file đó' % (len(A), len(clips), ' (%d kịch bản)' % len(used) if len(used) > 1 else ''))
        cnt = {}; na = nb = 0
        for c in clips:
            a = c['a']; key2 = (c['kb'], c['t']); cnt[key2] = cnt.get(key2, 0) + 1; c['n'] = cnt[key2]
            na += c['t'] == 'A'; nb += c['t'] == 'B'
            ext0 = os.path.splitext(a['name'])[1].lower()
            c['ext'] = ext0 if ext0 in ('.mp4', '.mov', '.m4v') else '.mp4'
            c['nm'] = '%s%02d - %s - %s%s' % (c['t'], c['n'], short(c['txt'], 90), safe(os.path.splitext(a['name'])[0], 60), c['ext'])  # A01 - lời thoại / mô tả - tên file gốc
            c['dst'] = fold.get(c['kb'], loc)
            c['src'] = os.path.join(TMP, 'src_%03d%s' % (a['i'], ext0 or '.mp4'))
            c['segs'] = speech_cut(a, c['keep']) if (c['t'] == 'A' or a['segs']) else c['keep']
            c['whole'] = len(c['segs']) == 1 and c['segs'][0][0] < .3 and c['segs'][0][1] > a['dur'] - .3
        work = [c for c in clips if not c['whole']]
        for c in clips:
            if c['whole']: cf = drive('files/%s/copy' % c['a']['id'], {'name': c['nm'], 'parents': [c['dst']], 'appProperties': dict(AP, by='', byName='', uid='', own='')}, params={'fields': FIELDS}); ix([cf]); outs.append((c['t'], cf['id'])); log('  ✓', c['nm'], '(chép nguyên bản)')
        def send(path, c, k):  # tải lên ngay khi xong (chạy song song với cắt video sau)
            uf = upload(path, c['nm'], c['dst'], meta(c)); os.remove(path); ix([uf]); outs.append((c['t'], uf['id'])); log('  ✓ đã đưa lên', c['nm']); prog(loc, 'Đã xong %d / %d file' % (k + 1, len(work)))
        with ThreadPoolExecutor(1) as dl:  # tải sẵn video kế tiếp trong lúc cắt video hiện tại
            fut = {}
            def pre(k):
                if k < len(work) and k not in fut: fut[k] = dl.submit(download, work[k]['a']['id'], work[k]['a']['size'], work[k]['src'])
            pre(0)
            for k, c in enumerate(work):
                fut[k].result(); pre(k + 1); a = c['a']; out = os.path.join(TMP, 'out%02d%s' % (k, c['ext']))
                c['qa'] = build(a, c, out)
                os.remove(c['src']); ups.append(up.submit(send, out, c, k))
        for f in ups: f.result()
    except Exception:
        up.shutdown(wait=False)
        try: drive('files/' + loc, {'trashed': True}, method='PATCH')
        except Exception: pass
        raise
    up.shutdown()
    secs, now = time.time() - t0, time.time()
    kbl = ''.join('\n   %d. %s: %d file' % (n, kbs.get(kb) or 'Kịch bản %d' % n, sum(1 for c in clips if c['kb'] == kb)) for n, kb in enumerate(used, 1)) if len(used) > 1 else ''
    rep = ('✂️ AI LỌC SOURCE XONG\n📁 %s › %s\n🎬 %d video gốc → %d file lọc (%d A-roll, %d B-roll)' % (jb.get('src') or '', jb['name'], len(vids), na + nb, na, nb) + kbl +
           ('\n🎯 ' + str(plan.get('muc_dich'))[:200] if plan.get('muc_dich') else '') +
           ('\n⏱ Video cuối tải lên %s → xong %s: %d phút (máy làm %d phút)' % (hm(jb['last']), hm(now), round((now - jb['last']) / 60), max(1, round(secs / 60))) if now - jb['last'] < 6 * 3600 else
            '\n⏱ Thư mục có sẵn từ %s – máy lọc xong trong %d phút' % (hm(jb['last']), max(1, round(secs / 60)))) +
           '\n🔗 ' + ((ix(link=loc) or {}).get('link') or SITE + '/_mo/' + loc))
    im = [i for t, i in sorted(outs, key=lambda x: x[0])][:16]
    drive('files/' + loc, {'description': rep, 'appProperties': dict({'locRep': '0', 'locRun': None}, **{'locI%d' % (k + 1): '.'.join(im[k * 3:k * 3 + 3]) for k in range(6)})}, method='PATCH')
    mark(jb['fid'], locDone=int(now), locV=LOC_V, locL='1', locOut=loc, locFail=None, locErr=None, locFailT=None)
    bad = [c for c in clips if c.get('qa')]
    if bad: tsay('⚠️ AI LỌC – còn %d file chưa sửa hết lỗi sau khi tự làm lại\n📁 %s\n%s' % (len(bad), title, '\n'.join('• %s: %s' % (c['nm'], qa_txt(c['qa'])) for c in bad[:8])))
    log('✓ Xong', title, '· %d file · %.1f phút' % (na + nb, secs / 60))
    flush_reports()

# ---------- bản 262 (chủ dặn): tự rà lại các file AI lọc đã có – đen / đứng hình đầu video, hình tiếng lệch, cắt giữa câu → tự lọc lại RIÊNG file đó ----------
QAQ = "appProperties has { key='ailoc' and value='1' } and trashed=false and mimeType contains 'video/'"
def qa_list():
    try: return [f for f in listq(QAQ, 'id,name,parents,appProperties,size,mimeType,createdTime', corpora()) if (f.get('appProperties') or {}).get('locQa') != '1']
    except Exception as e: log('  không rà được file lọc cũ:', e); return []
def find_src(f):  # file lọc cũ → thư mục Lọc → thư mục chứa video gốc → video gốc theo tên (A01 - nội dung - tên gốc)
    ap = f.get('appProperties') or {}; par = (f.get('parents') or [''])[0]; loc = None
    for g in range(3):
        d = drive('files/' + par, params='supportsAllDrives=true&fields=id,name,parents,appProperties')
        if re.match(r'^loc\b', norm1(d['name'])): loc = d; break
        par = (d.get('parents') or [''])[0]
    if not loc: return None, None
    jf = (loc.get('parents') or [''])[0]
    if ap.get('locSrc'):
        v = drive('files/' + ap['locSrc'], params='supportsAllDrives=true&fields=id,name,size,videoMediaMetadata')
        return v, jf
    m = re.match(r'^[AB]\d{2} - .* - (.+?)(\.[A-Za-z0-9]{2,5})?$', f['name']); stem = m.group(1) if m else ''
    if not stem: return None, jf
    st = [jf]
    for g in range(30):
        if not st: break
        d = st.pop(0)
        for c in listq("'%s' in parents and trashed=false" % d, 'id,name,mimeType,size,videoMediaMetadata,appProperties', corpora()):
            if c['mimeType'] == FOLDER:
                if not re.match(r'^loc\b', norm1(c['name'])) and not mine_ap(c.get('appProperties')): st.append(c['id'])
            elif is_video(c) and safe(os.path.splitext(c['name'])[0], 60) == stem: return c, jf
    return None, jf
def regen_one(f, key, models, q):
    v, jf = find_src(f)
    if not v: log('  không tìm được video gốc của', f['name']); return False
    vm = v.get('videoMediaMetadata') or {}; vr = {'id': v['id'], 'name': v['name'], 'dir': '', 'size': int(v.get('size') or 0), 'dur': int(vm.get('durationMillis') or 0) / 1000}
    shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
    a = analyze(1, vr); a['segs'] = transcribe(a['wav']); ap = f.get('appProperties') or {}; t = 'A' if f['name'].startswith('A') else 'B'
    keep = None
    if ap.get('locSg1'):
        try: keep = [[float(x) for x in z.split('-')] for z in ''.join(ap.get('locSg%d' % k) or '' for k in range(1, 5)).split(';') if z]
        except Exception: keep = None
    if not keep:
        try: plan = gemini(key, models, {'title': 'Lọc lại riêng 1 video', 'vids': [a]}) if key else fallback([a])
        except Exception: plan = fallback([a])
        cl = (plan.get('clips') or fallback([a])['clips'])[0]
        keep = [[max(0.0, float(r[0])), min(a['dur'], float(r[1]))] for r in (cl.get('giu') or [[0, a['dur']]]) if float(r[1]) - float(r[0]) >= .8] or [[0, a['dur']]]
        keep = speech_cut(a, sorted(keep)) if (t == 'A' or a['segs']) else sorted(keep)
    ext0 = os.path.splitext(v['name'])[1].lower() or '.mp4'
    c = dict(t=t, a=a, segs=keep, nm=f['name'], dst=(f.get('parents') or [''])[0], src=os.path.join(TMP, 'src_regen' + ext0))
    download(v['id'], vr['size'], c['src']); out = os.path.join(TMP, 'regen' + os.path.splitext(f['name'])[1].lower() if os.path.splitext(f['name'])[1].lower() in ('.mp4', '.mov', '.m4v') else os.path.join(TMP, 'regen.mp4'))
    left = build(a, c, out); os.remove(c['src'])
    uf = upload(out, f['name'], c['dst'], meta(c)); os.remove(out); ix([uf])
    drive('files/' + f['id'], {'trashed': True}, method='PATCH'); ix(dele=[f['id']])
    log('  ✓ đã lọc lại', f['name'], '(lỗi cũ: %s)' % qa_txt(q))
    return uf, left
def qa_old(key, models, until):
    L = qa_list(); fixed = []
    if L: log('Tự rà lại %d file AI lọc' % len(L))
    for f in L:
        if time.time() > until: break
        try:
            q = qa(fin(f['id']), aroll=f['name'].startswith('A'), full=False)
            if not q: mark(f['id'], locQa='1'); continue
            log('  ⚠', f['name'], '→', qa_txt(q))
            r = regen_one(f, key, models, q)
            if r: fixed.append('• %s: %s%s' % (f['name'], qa_txt(q), ' (vẫn còn: %s)' % qa_txt(r[1]) if r[1] else ''))
            else: mark(f['id'], locQa='x')
        except Exception as e:
            log('  ✗ rà / lọc lại lỗi', f['name'], e); tsay('❌ AI lọc: tự rà lại file lỗi không xong\n🎬 %s\n%s' % (f['name'], str(e)[:200]))
            try: mark(f['id'], locQa='x')
            except Exception: pass
    if fixed: tsay('🔁 AI LỌC – TỰ RÀ LẠI FILE ĐÃ LỌC: phát hiện lỗi và đã lọc lại %d file\n%s' % (len(fixed), '\n'.join(fixed[:12])))
    return len(L)

# ---------- máy GitHub tự cập nhật máy chủ Apps Script (không cần máy chủ gọi mạng → không dính hạn mức) ----------
def verno(v):  # số chính + số phụ (263.1 = lần đẩy giữa chừng của bản 263)
    m = re.search(r'bản\s*(\d+)(?:\.(\d+))?', str(v or '')); return (int(m.group(1)) + int(m.group(2) or 0) / 1000) if m else 0
def server_ver():
    try: return http(API + '?ping=1', timeout=60).get('ver') or ''
    except Exception as e: log('  không hỏi được bản máy chủ:', str(e)[:100]); return ''
def server_sync():
    try:
        meta = json.loads(urllib.request.urlopen(SITE + '/cg.txt?t=%d' % time.time(), timeout=60).read())
        cur = server_ver()
        if '--sync' in sys.argv: log('Máy chủ:', cur or '?', '· web:', meta.get('ver'))
        if not cur or verno(meta.get('ver')) <= verno(cur): return
        c = cfg(); src = c['src']
        if hashlib.sha256(src.encode('utf-8')).hexdigest() != meta.get('sha') or c['ver'] != meta.get('ver'): log('  gói máy chủ trên web chưa khớp, để lượt sau'); return
        log('Máy chủ đang %s, web có %s → máy GitHub tự cập nhật máy chủ' % (cur, meta['ver']))
        S = 'https://script.googleapis.com/v1/projects/' + SCRIPT_ID; H = lambda: {'Authorization': 'Bearer ' + tok()}
        old = http(S + '/content', headers=H())
        files = [dict(f, source=src) if f.get('type') == 'SERVER_JS' and 'const BOT_VER = ' in (f.get('source') or '') else f for f in old['files']]
        for f in files:  # bật dịch vụ Drive v3 (đọc Drive không tốn hạn mức gọi mạng của máy chủ)
            if f.get('type') == 'JSON' and f.get('name') == 'appsscript':
                try:
                    mf = json.loads(f['source']); sv = mf.setdefault('dependencies', {}).setdefault('enabledAdvancedServices', [])
                    if not any(x.get('serviceId') == 'drive' for x in sv): sv.append({'userSymbol': 'Drive', 'serviceId': 'drive', 'version': 'v3'}); f['source'] = json.dumps(mf, indent=2, ensure_ascii=False); log('  bật dịch vụ Drive cho máy chủ')
                except Exception as e: log('  không sửa được cấu hình dự án:', e)
        if not any(f.get('source') == src for f in files): raise RuntimeError('không thấy tệp code chính')
        http(S + '/content', {'files': files}, H(), 'PUT')
        v = http(S + '/versions', {'description': meta['ver'] + ' (máy GitHub cập nhật)'}, H(), 'POST')
        wd = (re.search(r"const WEB_DEP = '([^']+)'", src) or [None, ''])[1]
        deps = [d for d in http(S + '/deployments', headers=H()).get('deployments', []) if any(e.get('entryPointType') == 'WEB_APP' for e in d.get('entryPoints', [])) and (d.get('deploymentConfig') or {}).get('versionNumber')]
        dep = next((d for d in deps if d['deploymentId'] == wd), None) or sorted(deps, key=lambda d: d.get('updateTime', ''))[-1]
        oldv = dep['deploymentConfig']['versionNumber']
        put = lambda n, d: http(S + '/deployments/' + dep['deploymentId'], {'deploymentConfig': {'scriptId': SCRIPT_ID, 'versionNumber': n, 'manifestFileName': 'appsscript', 'description': d}}, H(), 'PUT')
        put(v['versionNumber'], meta['ver'])
        for k in range(15):
            time.sleep(6)
            if server_ver() == meta['ver']: log('✓ Máy chủ đã lên', meta['ver']); return
        log('  máy chủ chưa trả lời bản mới → quay lại bản cũ'); put(oldv, 'quay lại bản cũ'); http(S + '/content', {'files': old['files']}, H(), 'PUT')
    except Exception as e: log('  tự cập nhật máy chủ lỗi:', str(e)[:200])

# Đóng gói Drive theo việc + dọn bộ nhớ đệm về đúng nhà (bản 260, chủ yêu cầu). Máy chủ làm, máy GitHub chỉ gọi lặp tới khi xong.
# Chưa có tệp pkg_go trong repo → chỉ ĐẾM (in ra log, không đụng Drive); có pkg_go → làm thật (chỉ tạo thư mục + chuyển file, không xóa gì).
def pkg():
    go = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pkg_go'))
    t0, tot, n = time.time(), {}, 0
    while time.time() - t0 < (20 if go else 4) * 60:
        try: r = api('pkgRun', go=1 if go else 0, budget=140)
        except Exception as e: log('  đóng gói Drive: máy chủ chưa sẵn sàng –', str(e)[:160]); return
        n += 1
        log('📦 Đóng gói Drive %s · lượt %d: bọc %d video, đổi tên %d thư mục, kịch bản %d, đệm chuyển %s, không rõ nhà %s, thư mục đệm mới %d, nơi đến %d, %ss%s' % (
            'LÀM THẬT' if go else 'CHỈ ĐẾM', n, r.get('wrap', 0), r.get('ren', 0), r.get('docs', 0), json.dumps(r.get('mv'), ensure_ascii=False), json.dumps(r.get('orphan'), ensure_ascii=False), r.get('mcNew', 0), r.get('dests', 0), r.get('secs'), ' · còn tiếp' if r.get('more') else ''))
        for x in (r.get('wrapL') or [])[:12]: log('   • bọc:', x)
        for x in (r.get('docsL') or [])[:8]: log('   • kịch bản:', x)
        for x in (r.get('err') or [])[:20]: log('   ✗', x)
        for k in ('wrap', 'docs', 'ren'): tot[k] = tot.get(k, 0) + (r.get(k) or 0)
        tot['mv'] = tot.get('mv', 0) + sum((r.get('mv') or {}).values())
        if not go or not r.get('more'): break
    if go and (tot.get('wrap') or tot.get('docs') or tot.get('mv', 0) >= 100):  # chỉ báo khi có thay đổi đáng kể (bản nhẹ mới tạo được dọn về hằng ngày, không báo lẻ tẻ)
        tsay('📦 ĐÓNG GÓI DRIVE THEO VIỆC: bọc %d video vào thư mục việc, %d file kịch bản, chuyển %d file bộ nhớ đệm về đúng việc.' % (tot.get('wrap', 0), tot.get('docs', 0), tot.get('mv', 0)))

# ---------- bản 263 (chủ dặn): bộ nhớ đệm ảnh nhỏ – tạo sẵn ảnh 480px cho mọi video / ảnh, lưu ở thư mục hệ thống; EdgeOne phát; file gốc xóa thì ảnh nhỏ xóa theo ----------
def tc_img(fid, mime):
    try:
        tl = drive('files/' + fid, params={'fields': 'thumbnailLink'}).get('thumbnailLink')
        if tl:
            req = urllib.request.Request(re.sub(r'=s\d+$', '', tl) + '=s480', headers={'Authorization': 'Bearer ' + tok()})
            with urllib.request.urlopen(req, timeout=60) as r: b = r.read()
            if len(b) > 800: return b
    except Exception: pass
    if shutil.which('ffmpeg') and (mime.startswith('video/') or mime.startswith('image/')):  # Drive chưa có ảnh xem trước → tự lấy 1 khung hình
        out = '/tmp/tc_%s.jpg' % fid
        try:
            run(['ffmpeg', '-y', '-v', 'error'] + fin(fid, ss=1 if mime.startswith('video/') else None) + ['-frames:v', '1', '-vf', 'scale=480:-2', '-q:v', '5', out], timeout=180)
            b = open(out, 'rb').read(); os.remove(out); return b if len(b) > 800 else None
        except Exception: return None
    return None
def tc_put(b, fid, parent, old=''):
    if old:  # file đổi → thay nội dung ảnh nhỏ cũ (giữ nguyên id)
        try: http(G + '/upload/drive/v3/files/' + old + '?uploadType=media&supportsAllDrives=true&fields=id', bytes(b), {'Authorization': 'Bearer ' + tok(), 'Content-Type': 'image/jpeg'}, 'PATCH'); return old
        except Exception: pass
    bd = 'tc' + hashlib.md5(fid.encode()).hexdigest()[:12]
    body = ('--%s\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' % bd).encode() + json.dumps({'name': fid + '.jpg', 'parents': [parent], 'appProperties': {'tcOf': fid}}).encode() + ('\r\n--%s\r\nContent-Type: image/jpeg\r\n\r\n' % bd).encode() + bytes(b) + ('\r\n--%s--' % bd).encode()
    return http(G + '/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id', body, {'Authorization': 'Bearer ' + tok(), 'Content-Type': 'multipart/related; boundary=' + bd})['id']
def tcache(budget=240):
    t0 = time.time()
    try: r = api('tcNeed', limit=400)
    except Exception as e: log('  ảnh nhỏ: máy chủ chưa sẵn sàng –', str(e)[:160]); return
    ok = []
    for fid, tid in (r.get('gone') or []):  # file gốc đã xóa → xóa ảnh nhỏ theo
        try: drive('files/' + tid, None, 'DELETE'); ok.append(fid)
        except Exception as e:
            if '404' in str(e): ok.append(fid)
            else: log('  không xóa được ảnh nhỏ', tid, str(e)[:120])
    if ok: api('tcDel', ids=ok); log('🖼 Đã xóa %d ảnh nhỏ của file đã bị xóa' % len(ok))
    need, done, n = r.get('need') or [], [], 0
    def one(it):
        if time.time() - t0 > budget: return None
        fid, name, mime, size, old = it
        b = tc_img(fid, mime)
        return [fid, tc_put(b, fid, r['folder'], old), str(size)] if b else None
    with ThreadPoolExecutor(8) as ex:
        for f in as_completed([ex.submit(one, it) for it in need]):
            try: x = f.result()
            except Exception as e: x = None; log('  ảnh nhỏ lỗi:', str(e)[:120])
            if x: done.append(x)
            if len(done) >= 40: api('tcSet', rows=done); n += len(done); done = []
    if done: api('tcSet', rows=done); n += len(done)
    left = max(0, (r.get('left') or 0) - n)
    if need or ok: log('🖼 Ảnh nhỏ bộ nhớ đệm: tạo %d / %d, còn chờ %d' % (n, len(need), left))
    return left if n else 0

def main():
    check = '--check' in sys.argv
    if '--quick' not in sys.argv: server_sync()  # máy đồng bộ nhanh: bước trước đã cập nhật máy chủ rồi
    if '--sync' in sys.argv: return
    if '--quick' in sys.argv:  # bản 263 (chủ dặn): đồng bộ ngay khi có thay đổi (máy ping, hàng chờ riêng – không kẹt sau AI lọc)
        try: pkg()
        except Exception as e: log('đóng gói Drive lỗi:', e)
        t1 = time.time()  # nhiều đợt trong 1 lượt (tối đa ~10 phút) cho nhanh phủ hết kho
        while time.time() - t1 < 10 * 60:
            try: left = tcache(budget=min(240, 10 * 60 - (time.time() - t1)))
            except Exception as e: log('ảnh nhỏ lỗi:', e); break
            if not left: break
        return
    repair_lost()
    fix_old()
    flush_reports()
    if check:
        L = scan(); n = len(L); nq = len(qa_list()); log('Buổi quay cần lọc:', n, '· file lọc cần tự rà lại:', nq)
        if os.environ.get('LOC_ON') != '1':  # bản 263.41: máy lọc tắt – máy chạy AI DỰNG project CapCut
            import dung; nd = dung.pending(); log('Buổi quay chờ AI dựng:', nd); n += nd; nq = 0
        if (root_info().get('appProperties') or {}).get('locHi') != '2':  # báo trạng thái 1 lần khi lên cách báo mới
            tsay('📋 AI LỌC – TRẠNG THÁI: ' + ('đang có %d buổi quay chờ lọc, máy GitHub bắt đầu ngay:\n' % n + '\n'.join('• %s › %s (%d video)' % (j['src'], j['name'], len(j['videos'])) for j in L[:10]) if n else 'không còn buổi quay nào chờ lọc, máy GitHub đang nghỉ.') + '\nTừ giờ: bắt đầu lọc, có lỗi, lọc xong đều báo ở nhóm này.')
            mark(ROOT, locHi='2')
        with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as w: w.write('todo=%d\n' % (1 if n or nq else 0))
        return
    c = cfg(); key = c['gem']; models = gem_models(key) if key else []
    log('Gói máy chủ trên web:', c['ver'], '· Gemini:', ', '.join(models[:3]) or 'không có')
    done = fails = 0; L = [None]
    while (time.time() - T0) / 60 < MAXMIN - 60:
        L = scan(); log('Buổi quay cần lọc:', len(L))
        if not L: break
        jb = L[0]; jb['left'] = len(L) - 1; server_sync()
        try: job(jb, key, models); done += 1
        except Exception as e:
            log('✗ lỗi:', e); fails += 1
            try:
                mark(jb['fid'], locFail=jb['nfail'] + 1, locFailT=int(time.time()), locErr=str(e)[:100])
                tsay('❌ AI LỌC SOURCE LỖI\n📁 %s › %s\n%s\n%s' % (jb.get('src') or '', jb['name'], str(e)[:300], 'Tự thử lại sau 20 phút.' if jb['nfail'] + 1 < FAIL_MAX else 'Đã thử %d lần, tạm bỏ qua (cần người xem).' % FAIL_MAX))
            except Exception as e2: log('  không ghi được lỗi:', e2)
    log('Hết việc lọc (%d buổi quay xong)' % done)
    if os.environ.get('LOC_ON') != '1':
        import dung
        try: dung.run(key, models, T0 + (MAXMIN - 10) * 60)
        except Exception as e: log('AI dựng hỏng:', e)
        return
    while not L and (time.time() - T0) / 60 < MAXMIN - 45:  # bản 263: rà lại file lọc cũ từng đợt 3 phút, giữa các đợt xem có buổi quay mới không → buổi mới không phải chờ hàng giờ
        if not qa_list(): break
        try: qa_old(key, models, min(time.time() + 180, T0 + (MAXMIN - 45) * 60))
        except Exception as e: log('tự rà lại lỗi:', e); break
        L2 = scan()
        if L2:
            jb = L2[0]; jb['left'] = len(L2) - 1
            try: job(jb, key, models); done += 1
            except Exception as e: log('✗ lỗi:', e); fails += 1
    if L: tsay('⏸ AI LỌC: lượt chạy GitHub hết giờ, còn %d buổi quay chờ – lượt sau tự làm tiếp (%d buổi xong ở lượt này).' % (len(L), done))
    elif done or fails: tsay('✅ AI LỌC: ĐÃ XONG HẾT – không còn buổi quay nào chờ lọc\n(%d buổi xong%s). Máy GitHub nghỉ; thư mục Source mới tải lên sẽ tự được lọc và báo ở đây.' % (done, ', %d buổi lỗi' % fails if fails else ''))

if __name__ == '__main__':
    if '--fail' in sys.argv:  # bước cài đặt trên GitHub hỏng (gọi từ loc.yml khi failure())
        try: tsay('❌ AI LỌC: máy GitHub lỗi khi chuẩn bị (cài ffmpeg / Whisper hoặc mạng). Lượt sau tự chạy lại.')
        except Exception as e: log('không báo được:', e)
        sys.exit(0)
    try: main()
    except Exception as e:
        log('✗ lượt chạy hỏng:', e)
        try: tsay('❌ AI LỌC: lượt chạy trên GitHub bị hỏng giữa chừng\n%s\nLượt sau tự chạy lại (thư mục đang dở sẽ được lọc lại).' % str(e)[:300])
        except Exception: pass
        raise
