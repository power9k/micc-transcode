# XEM & NGHE KỸ SOURCE (bản nâng cấp, 11/11/2026) – chạy ngay sau loc.analyze khi khung hình + âm thanh còn trên máy
#  - tờ ảnh mẫu: MỌI khung hình chính (keyframe) của video, 12 khung / tờ, có ghi giây → Claude xem bằng mắt
#  - mặt người theo từng khung chính (OpenCV YuNet) → tracking, chữ né mặt
#  - nhãn âm thanh theo từng giây (im lặng / gió-ù / ồn / có nhịp nhạc / giọng nói) – đo bằng phổ tần, không tốn AI
#  - phân tích nhạc nền: BPM, nhịp, kick, snare, đoạn lắng / sôi, điểm dồn (drop)
import os, io, glob, base64, json, math, subprocess, sys, urllib.request
class _NP:   # numpy nạp khi cần (bước kiểm tra nhanh chạy trước khi cài numpy)
    def __getattr__(self, k):
        import numpy; return getattr(numpy, k)
np = _NP()

YUNET = ['https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx', 'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx']
_DET = []

def _cv2():
    try:
        import cv2; return cv2
    except Exception:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'opencv-python-headless'], capture_output=True)
        try:
            import cv2; return cv2
        except Exception: return None

def _detector(cv2, w, h):
    if not _DET:
        p = os.path.join(os.environ.get('LOC_TMP', '/tmp/loc'), 'yunet.onnx')
        try:
            for u in YUNET:
                if os.path.exists(p) and os.path.getsize(p) > 100000: break
                try: urllib.request.urlretrieve(u, p)
                except Exception: pass
            _DET.append(cv2.FaceDetectorYN.create(p, '', (w, h), 0.7, 0.3, 50))
        except Exception: _DET.append(None)
    d = _DET[0]
    if d is not None: d.setInputSize((w, h))
    return d

def sheets(ims, kt, per=12, cols=4):
    from PIL import Image, ImageDraw
    out = []
    for g in range(0, len(ims), per):
        grp = ims[g:g + per]; tiles = []
        for k, p in enumerate(grp):
            im = Image.open(p).convert('RGB'); im.thumbnail((240, 240)); tiles.append((im, kt[g + k] if g + k < len(kt) else 0))
        tw = max(t[0].width for t in tiles); th = max(t[0].height for t in tiles)
        rows = math.ceil(len(tiles) / cols); cv = Image.new('RGB', (cols * tw, rows * th), (12, 12, 12)); dr = ImageDraw.Draw(cv)
        for k, (im, t) in enumerate(tiles):
            x, y = (k % cols) * tw, (k // cols) * th; cv.paste(im, (x, y))
            dr.rectangle([x, y, x + 52, y + 16], fill=(0, 0, 0)); dr.text((x + 3, y + 2), '%.1fs' % t, fill=(255, 230, 80))
        bio = io.BytesIO(); cv.save(bio, 'JPEG', quality=55)
        out.append(dict(ts=[round(t, 2) for _, t in tiles], tw=tw, th=th, cols=cols, b=base64.b64encode(bio.getvalue()).decode()))
    return out

def faces(ims, kt):
    cv2 = _cv2()
    if cv2 is None: return []
    out = []
    for k, p in enumerate(ims):
        im = cv2.imread(p)
        if im is None: continue
        h, w = im.shape[:2]; d = _detector(cv2, w, h)
        if d is None: return []
        _, f = d.detect(im)
        if f is None or not len(f): continue
        x, y, fw, fh = max(f, key=lambda r: r[2] * r[3])[:4]
        out.append([round(float(kt[k]) if k < len(kt) else 0.0, 2), round(float(x + fw / 2) / w, 3), round(float(y + fh / 2) / h, 3), round(float(fw) / w, 3), round(float(fh) / h, 3)])
    return out

def _wav(path):
    import wave
    with wave.open(path) as w: sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x, sr

def sound_tags(wav, segs):
    # nhãn từng giây: giọng nói (theo Whisper) + đặc tính phổ: im lặng, gió/ù (năng lượng dồn < 150 Hz), ồn (phổ phẳng), có nhịp (nhạc / tiếng gõ đều)
    if not wav or not os.path.exists(wav): return []
    x, sr = _wav(wav); n = int(len(x) / sr); out = []
    speech = np.zeros(n + 1, bool)
    for s in segs or []:
        speech[int(s['s']):int(math.ceil(s['e'])) + 1] = True
    for i in range(n):
        f = x[i * sr:(i + 1) * sr]
        if len(f) < sr // 2: break
        rms = 20 * math.log10(float(np.sqrt(np.mean(f ** 2))) + 1e-9)
        sp = np.abs(np.fft.rfft(f * np.hanning(len(f)))) + 1e-9; fr = np.fft.rfftfreq(len(f), 1 / sr)
        low = float(sp[fr < 150].sum() / sp.sum()); flat = float(np.exp(np.mean(np.log(sp))) / np.mean(sp))
        env = np.abs(f[: len(f) // 160 * 160]).reshape(-1, 160).mean(1); od = np.maximum(0, np.diff(env))
        ac = np.correlate(od - od.mean(), od - od.mean(), 'full')[len(od) - 1:]
        rhythm = float(ac[25:100].max() / (ac[0] + 1e-9)) if len(ac) > 100 else 0
        t = []
        if rms < -45: t.append('im lặng')
        else:
            if speech[i]: t.append('giọng nói')
            if low > .55 and rms > -35: t.append('gió/ù')
            if flat > .35 and rms > -32: t.append('ồn')
            if rhythm > .45 and not speech[i]: t.append('có nhịp/nhạc')
        out.append(','.join(t) or 'âm nền nhỏ')
    runs = []   # gộp các giây liền nhau cùng nhãn: [[giây đầu, giây cuối, nhãn]]
    for i, t in enumerate(out):
        if runs and runs[-1][2] == t: runs[-1][1] = i + 1
        else: runs.append([i, i + 1, t])
    return runs

def music_map(path):
    # phân tích nhạc nền: BPM, nhịp, kick (dải trầm), snare (dải giữa-cao), đoạn lắng/sôi, điểm dồn
    tmp = path + '.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', path, '-ac', '1', '-ar', '22050', tmp], capture_output=True)
    x, sr = _wav(tmp); hop = 512; win = 2048
    nfr = 1 + (len(x) - win) // hop
    if nfr < 10: return {}
    idx = np.arange(win)[None, :] + hop * np.arange(nfr)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * np.hanning(win), axis=1)); fr = np.fft.rfftfreq(win, 1 / sr)
    def flux(lo, hi):
        b = S[:, (fr >= lo) & (fr < hi)]; d = np.maximum(0, np.diff(np.log1p(b), axis=0)).sum(1); return np.r_[0, d]
    full, kick, snare = flux(20, 11000), flux(30, 150), flux(1500, 5000)
    tt = (np.arange(nfr) * hop + win / 2) / sr   # mốc = giữa cửa sổ phân tích (chính xác ±12 ms)
    def peaks(v, k=1.6, gap=.12):
        th = v.mean() + k * v.std(); out = []
        for i in range(1, len(v) - 1):
            if v[i] > th and v[i] >= v[i - 1] and v[i] >= v[i + 1] and (not out or tt[i] - out[-1] > gap): out.append(round(float(tt[i]), 3))
        return out
    o = full - full.mean(); ac = np.correlate(o, o, 'full')[len(o) - 1:]
    lo_l, hi_l = int(60 / 180 * sr / hop), int(60 / 70 * sr / hop)
    lag = lo_l + int(np.argmax(ac[lo_l:hi_l])); bpm = round(60 * sr / hop / lag, 1); per = lag * hop / sr
    ph = max(range(lag), key=lambda p: full[p::lag].sum()); beats = [round(float(tt[p]), 3) for p in range(ph, nfr, lag)]
    rms = np.sqrt((x[: len(x) // sr * sr].reshape(-1, sr) ** 2).mean(1)); e = np.convolve(rms, np.ones(4) / 4, 'same')
    q = np.quantile(e, [.33, .66]); sec = []
    for i, v in enumerate(e):
        lab = 'lắng' if v < q[0] else ('vừa' if v < q[1] else 'sôi')
        if sec and sec[-1][2] == lab: sec[-1][1] = i + 1
        else: sec.append([i, i + 1, lab])
    sec2 = []   # gộp đoạn quá ngắn (< 3 s) vào đoạn trước cho dễ đọc
    for a_, b_, l_ in sec:
        if sec2 and (b_ - a_ < 3 or sec2[-1][2] == l_): sec2[-1][1] = b_
        else: sec2.append([a_, b_, l_])
    sec = sec2
    drops, de = [], np.diff(e) if len(e) > 2 else np.array([])
    for i in np.argsort(-de):   # điểm dồn: năng lượng tăng vọt, cách nhau ≥ 6 s
        if de[i] <= 0 or len(drops) >= 3: break
        if de[i] > .25 * de.max() and all(abs(int(i) + 1 - d) >= 6 for d in drops): drops.append(int(i) + 1)
    try: os.remove(tmp)
    except Exception: pass
    return dict(bpm=bpm, beat=round(per, 3), beats=beats, kicks=peaks(kick), snares=peaks(snare), sections=sec, drops=sorted(drops))

def perceive(a, segs):
    # gọi ngay sau loc.analyze (a['dir'] còn khung hình, a['wav'] còn âm thanh)
    ims = sorted(glob.glob(os.path.join(a.get('dir') or '', 'k*.jpg'))); kt = a.get('kt') or []
    r = {}
    try: r['sheets'] = sheets(ims, kt)
    except Exception as e: r['sheets'] = []; r['err_sheets'] = str(e)[:120]
    try: r['faces'] = faces(ims, kt)
    except Exception as e: r['faces'] = []; r['err_faces'] = str(e)[:120]
    try: r['sound'] = sound_tags(a.get('wav') if isinstance(a.get('wav'), str) else None, segs)
    except Exception as e: r['sound'] = []; r['err_sound'] = str(e)[:120]
    return r
