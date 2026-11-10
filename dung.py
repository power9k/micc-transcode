# AI DỰNG PROJECT CAPCUT (bản 1, 10/11/2026) – chạy trên máy GitHub cùng lượt với loc.py
# Mỗi buổi quay (thư mục con của "Source"), từ MỚI đến CŨ, buổi mới tải lên được ưu tiên ngay sau buổi đang làm:
#  1) ĐỌC: xem hình (khung chính, độ nét/rung) + chép lời có mốc từng chữ – đọc song song với bước dựng
#  2) GEMINI (theo QUY TẮC DỰNG của chủ): tự chia kịch bản (mỗi video < 2 phút) nếu không có file kịch bản,
#     chọn câu nói hay nhất (đủ ý, đúng diễn xuất), cảnh phụ khớp lời, chữ nhấn ý chính
#  3) DỰNG: bỏ ngập ngừng / ầm à, che vết cắt bằng giật zoom, cảnh phụ, chữ, nhạc, hiệu ứng âm thanh → draft CapCut
#  4) Đưa project vào thư mục buổi quay (1 phiên bản duy nhất) + thêm vào SETUP/CapCut projects.txt (máy nhân viên tự có lối tắt)
import os, sys, json, time, re, threading, queue, zipfile, base64, subprocess, unicodedata, urllib.request, urllib.parse
import loc as L

DV = '1'                                   # đổi số này = dựng lại mọi buổi quay
EXCL = {'16rYEIREpSv2N78zOi5cOoLlXn5qHzGK4', '1RkqwSNXvzJ8XFnUYuvQlQlh_B0oYhnR-'}   # Center Avenue KB1, KB2: chủ đã duyệt tay
SETUP_NAME, LIST_NAME, ENG_NAME = 'SETUP', 'CapCut projects.txt', 'engine.zip'
LIB = '1ZIROORo_epCYmpf55Q0reoT8gOfCwyEX'  # thư mục nhạc + hiệu ứng âm thanh + font mẫu (AI tải về của Center Avenue KB2)
LIB_SKIP = ('Phim ', 'Outro ')
DRV = 'G:/Drive của tôi/PHÒNG TRUYỀN THÔNG MICC'
SKIPDIR = re.compile(r'^(capcut|lọc|loc\b|bộ nhớ đệm|ai tải về|_ai)', re.I)
ENG = os.path.join(L.TMP, 'eng')
log = L.log

def lq(q, f='id,name,mimeType,size,createdTime,parents,appProperties,videoMediaMetadata(width,height,durationMillis)'):
    return L.listq(q + ' and trashed=false', f, L.corpora())
def kids(fid): return lq("'%s' in parents" % fid)
def get(fid, f='id,name,parents,appProperties'): return L.drive('files/' + fid, params={'fields': f})
def raw(fid):
    req = urllib.request.Request(L.durl(fid), headers={'Authorization': 'Bearer ' + L.tok()})
    with urllib.request.urlopen(req, timeout=300) as r: return r.read()
def put(name, parent, data, mime):  # tải file nhỏ lên Drive (multipart)
    b = '----micc%d' % time.time()
    body = ('--%s\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n%s\r\n--%s\r\nContent-Type: %s\r\n\r\n' % (
        b, json.dumps({'name': name, 'parents': [parent]}), b, mime)).encode() + data + ('\r\n--%s--' % b).encode()
    return L.http(L.G + '/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id', body,
                  {'Authorization': 'Bearer ' + L.tok(), 'Content-Type': 'multipart/related; boundary=' + b})
def update(fid, data, mime):
    return L.http(L.G + '/upload/drive/v3/files/' + fid + '?uploadType=media&supportsAllDrives=true', data,
                  {'Authorization': 'Bearer ' + L.tok(), 'Content-Type': mime}, method='PATCH')
def mkdir(name, parent): return L.drive('files', {'name': name, 'parents': [parent], 'mimeType': L.FOLDER}, params={'fields': 'id'})['id']
def safe(s, k=70): return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', str(s))).strip()[:k].strip()
def nf(s): return unicodedata.normalize('NFC', s or '')

# ---------------------------------------------------------------- tìm buổi quay
PATHS = {}
def path_of(fid):   # đường dẫn tương đối từ PHÒNG TRUYỀN THÔNG MICC
    if fid in PATHS: return PATHS[fid]
    parts, cur = [], fid
    for _ in range(30):
        if cur == L.ROOT: break
        f = get(cur, 'id,name,parents'); parts.append(nf(f['name'])); cur = (f.get('parents') or [L.ROOT])[0]
    PATHS[fid] = '/'.join(reversed(parts)); return PATHS[fid]
def scan():
    fol = lq("mimeType='%s'" % L.FOLDER, 'id,name,parents,appProperties,createdTime')
    by = {f['id']: f for f in fol}; ch = {}
    for f in fol:
        for p in f.get('parents') or []: ch.setdefault(p, []).append(f)
    memo = {L.ROOT: True}
    def under(fid, d=0):
        if fid in memo: return memo[fid]
        f = by.get(fid); r = bool(f and d < 40 and any(under(p, d + 1) for p in f.get('parents') or [])); memo[fid] = r; return r
    srcs = [f for f in fol if re.search(r'\bsources?\b', L.norm1(f['name'])) and under(f['id'])]
    out, now = [], time.time()
    for s in srcs:
        for sh in ch.get(s['id'], []):
            if SKIPDIR.match(nf(sh['name'])): continue
            ap = sh.get('appProperties') or {}
            if ap.get('dungV') == DV or int(ap.get('dungFail') or 0) >= 3: continue
            sub, st = [], [sh]
            while st:
                d = st.pop(); sub.append(d['id'])
                st += [c for c in ch.get(d['id'], []) if not SKIPDIR.match(nf(c['name']))]
            if EXCL & set(sub): continue
            out.append(dict(id=sh['id'], name=nf(sh['name']), src=nf(s['name']), dirs=sub, ap=ap))
    jobs = []
    for j in out:   # video trong buổi quay (cả thư mục con)
        vids, docs = [], []
        for d in j['dirs']:
            for c in kids(d):
                if L.is_video(c) and not c['name'].lower().endswith('.lrf'): vids.append(dict(c, dir=d))
                elif c['mimeType'] in ('application/vnd.google-apps.document', 'text/plain') or c['name'].lower().endswith(('.docx', '.txt')): docs.append(c)
        if not vids: continue
        last = max(L.ts(v['createdTime']) for v in vids)
        if now - last < L.SETTLE: continue   # còn đang tải lên
        jobs.append(dict(j, vids=vids, docs=docs, last=last))
    jobs.sort(key=lambda j: -j['last'])
    return jobs

# ---------------------------------------------------------------- 1) đọc source (song song với dựng)
def read(jb):
    t0 = time.time(); A = []
    vids = sorted(jb['vids'], key=lambda v: v['name'])
    from concurrent.futures import ThreadPoolExecutor
    def one(iv):
        i, v = iv
        a = L.analyze(i + 1, dict(id=v['id'], name=v['name'], size=int(v.get('size') or 0), dur=(v.get('videoMediaMetadata') or {}).get('durationMillis', 0) / 1000))
        a['vid'] = v; return a
    with ThreadPoolExecutor(3) as ex: A = list(ex.map(one, enumerate(vids)))
    for a in A: a['segs'] = L.transcribe(a['wav'])
    gb = sum(int(v.get('size') or 0) for v in vids) / 1e9
    log('  đọc xong %s: %d video, %.1f GB trong %.1f phút' % (jb['name'], len(A), gb, (time.time() - t0) / 60))
    jb['A'] = A; return jb

# ---------------------------------------------------------------- 2) Gemini chia kịch bản + chọn cảnh
RULES = '''QUY TẮC DỰNG CỦA CHỦ (bắt buộc):
- Mỗi kịch bản = 1 video DƯỚI 2 PHÚT (tổng A-roll 45–110 giây). Buổi quay dài (đào tạo, hội thảo) → tách thành nhiều tập, mỗi tập 1 ý trọn vẹn, có câu mở hút (hook) và kết.
- Nếu có file kịch bản: theo đúng kịch bản. Nếu thư mục con đặt tên "Kịch bản 1/2" thì mỗi thư mục con là 1 kịch bản.
- A-roll: chỉ lấy câu người nói ĐÚNG lời thoại, nói trôi chảy, diễn xuất tốt (không đứng nhẩm, không nói lại, không nhăn mặt). Mỗi câu nói lại nhiều lần → chọn 1 bản hay nhất. Giữ TRỌN câu, không cắt giữa câu.
- Cảnh phụ (B-roll) phải KHỚP lời đang nói. Không dùng cảnh có người đang nói câu khác. Mỗi cảnh dùng 1 lần, không lặp cảnh giống nhau.
- Không cố nhét cảnh: ít cảnh đẹp thì dùng ít.
- Chữ: KHÔNG chạy phụ đề theo lời. Chỉ 1 cụm nhấn ý chính mỗi 5–8 giây: "big" = TỪ KHÓA viết hoa ≤ 3 từ (số liệu, tên dự án, lợi ích), "small" = 1 dòng phụ ≤ 6 từ. Đúng chính tả tiếng Việt, trọn nghĩa.'''
SYS = '''Bạn là editor video ngắn (TikTok/Reels dọc 9:16) chuyên nghiệp của team truyền thông MICC (bất động sản + đào tạo).
Bạn nhận toàn bộ source của 1 buổi quay: lời thoại có mốc thời gian, chất lượng hình, ảnh khung hình. Hãy lên kế hoạch DỰNG các video ngắn.
''' + RULES + '''
Trả về JSON: {"scripts":[{"ten":"tên video ngắn gọn","aroll":[{"video":<số #>,"s":giây,"e":giây}],"broll":[{"video":<số #>,"s":giây,"e":giây,"luc":<giây của A-roll video nào đó: dạng [số #, giây]>}],"titles":[{"video":<số #>,"t":giây (lúc nói từ khóa, theo video gốc),"big":"TỪ KHÓA","small":"dòng phụ"}]}]}
- aroll theo đúng thứ tự phát. "s","e" theo giây của video gốc, bao trọn câu.
- broll "luc" = [số video A-roll, giây trong video đó] lúc cảnh phụ bắt đầu che hình (tiếng vẫn là A-roll); mỗi cảnh phụ 1.5–3.5 giây.
- Không có kịch bản dựng được (source hỏng / chỉ thử máy) → {"scripts":[]}.'''
def doc_text(jb):
    out = []
    for d in jb['docs'][:3]:
        try:
            if d['mimeType'] == 'application/vnd.google-apps.document':
                req = urllib.request.Request(L.G + '/drive/v3/files/%s/export?mimeType=text/plain' % d['id'], headers={'Authorization': 'Bearer ' + L.tok()})
                with urllib.request.urlopen(req, timeout=120) as r: out.append('FILE KỊCH BẢN "%s":\n%s' % (d['name'], r.read().decode('utf-8', 'replace')[:12000]))
            elif d['name'].lower().endswith('.txt'): out.append('FILE KỊCH BẢN "%s":\n%s' % (d['name'], raw(d['id']).decode('utf-8', 'replace')[:12000]))
        except Exception as e: log('  không đọc được file kịch bản', d['name'], e)
    return '\n\n'.join(out)
def plan(jb, key, models):
    parts = [{'text': 'Kênh / dự án: %s\nBuổi quay: %s\nCó %d video.\n%s' % (path_of(jb['id']), jb['name'], len(jb['A']), doc_text(jb) or '(không có file kịch bản – tự phân tích)')}]
    for a in jb['A']:
        parts.append({'text': L.summary(a)[:6000]})
        for t, b in a['thumbs'][:3]: parts += [{'text': '#%d lúc %.1fs:' % (a['i'], t)}, {'inline_data': {'mime_type': 'image/jpeg', 'data': b}}]
    body = {'systemInstruction': {'parts': [{'text': SYS}]}, 'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'temperature': .3, 'maxOutputTokens': 30000, 'responseMimeType': 'application/json'}}
    last = ''
    for rnd in range(3):
        for m in models:
            try:
                j = L.http(L.GEM + 'models/' + m + ':generateContent', body, {'x-goog-api-key': key}, timeout=600)
                txt = ''.join(p.get('text', '') for p in ((j.get('candidates') or [{}])[0].get('content') or {}).get('parts', []))
                return json.loads(re.sub(r'^```(json)?|```$', '', txt.strip())).get('scripts') or []
            except Exception as e: last = '%s: %s' % (m, e); log('  Gemini lỗi:', last)
        time.sleep(20 * (rnd + 1))
    raise RuntimeError('Gemini không lên được kế hoạch dựng (' + last + ')')

# ---------------------------------------------------------------- 3) dựng → plan cho engine
CW, CH = 1080, 1920
def s0(a): w, h = a.get('w') or 1080, a.get('h') or 1920; return (w / h) / (CW / CH) if w / h > CW / CH + .01 else 1.0
def words(a, s, e): return [w for sg in a['segs'] for w in sg['w'] if w[0] >= s - .05 and w[1] <= e + .05]
def tighten(a, s, e):   # bỏ ngập ngừng, ầm à: giữ cụm có chữ, khoảng lặng > 0.3 s rút về 0.12 s
    W = [w for w in words(a, s, e) if L.norm(w[2]) not in L.FILL]
    if not W: return [(s, e)]
    iv = []
    for w in W:
        if iv and w[0] - iv[-1][1] <= .3: iv[-1][1] = w[1]
        else: iv.append([w[0], w[1]])
    return [(max(s, x - .06), min(e, y + .1)) for x, y in iv if y - x > .12]
def build_plan(jb, sc, proj, adir):
    A = {a['i']: a for a in jb['A']}; media, shots, speech, titles, sfx = {}, [], [], [], []
    def key(a):
        k = 'V%d' % a['i']
        if k not in media:
            media[k] = dict(path=DRV + '/' + path_of(a['vid']['dir']) + '/' + nf(a['name']), dur=a['dur'], w=a.get('w') or 1080, h=a.get('h') or 1920,
                            kind='video', has_audio=bool(a.get('wav')), name=nf(a['name']), S0=s0(a))
        return k
    t, pieces, z = 0.0, [], 0
    for it in sc.get('aroll', []):
        a = A.get(int(it.get('video', 0))); s, e = float(it.get('s', 0)), float(it.get('e', 0))
        if not a or e - s < .6 or e > a['dur'] + .5: continue
        for x, y in tighten(a, s, min(e, a['dur'] - .05)):
            d = y - x; k = key(a); m = 1.0 if z % 2 == 0 else 1.12; z += 1   # giật zoom che vết cắt
            shots.append(dict(media=k, src=round(x, 3), t0=round(t, 3), t1=round(t + d, 3), line='A', keys=[[round(t, 3), m, .5, .45, 0.0], [round(t + d, 3), m * 1.02, .5, .45, 0.0]], punch_abs=[]))
            speech.append(dict(media=k, src_in=round(x, 3), t0=round(t, 3), t1=round(t + d, 3), vol=1.0))
            pieces.append((a['i'], x, y, t)); t += d
        if t > 118: break
    if t < 15: return None
    total = round(t, 3)
    def tl(vi, st):   # giây video gốc → giây trên timeline
        for i, x, y, t0 in pieces:
            if i == vi and x - .2 <= st <= y + .2: return t0 + max(0, min(y, st) - x)
        return None
    used = set()
    for b in sc.get('broll', []):   # cảnh phụ che hình (tiếng vẫn là A-roll)
        a = A.get(int(b.get('video', 0))); at = b.get('luc') or [0, 0]
        if not a or a['i'] in used: continue
        T = tl(int(at[0]), float(at[1])) if isinstance(at, list) and len(at) == 2 else None
        if T is None: continue
        s, e = float(b.get('s', 0)), float(b.get('e', 0)); d = min(3.5, max(1.5, e - s), total - T - .2)
        if d < 1.2 or s + d > a['dur']: continue
        k = key(a); used.add(a['i']); new = []
        for sh in shots:
            if sh['t1'] <= T or sh['t0'] >= T + d: new.append(sh); continue
            if sh['t0'] < T: new.append(dict(sh, t1=round(T, 3), keys=[[sh['t0']] + sh['keys'][0][1:], [round(T, 3)] + sh['keys'][-1][1:]]))
            if sh['t1'] > T + d: new.append(dict(sh, src=round(sh['src'] + T + d - sh['t0'], 3), t0=round(T + d, 3), keys=[[round(T + d, 3)] + sh['keys'][0][1:], [sh['t1']] + sh['keys'][-1][1:]]))
        new.append(dict(media=k, src=round(s, 3), t0=round(T, 3), t1=round(T + d, 3), line='B', keys=[[round(T, 3), 1.0, .5, .5, 0.0], [round(T + d, 3), 1.06, .5, .5, 0.0]], punch_abs=[]))
        shots = sorted(new, key=lambda x: x['t0']); sfx.append(dict(file='SFX whoosh dien anh 01.wav', t=max(0, round(T - .35, 3)), vol=.2, dur=1.334127))
    for ti in sc.get('titles', [])[:20]:
        T = tl(int(ti.get('video', 0)), float(ti.get('t', 0)))
        big = safe(ti.get('big', ''), 32).upper(); small = safe(ti.get('small', ''), 48)
        if T is None or not big: continue
        if titles and T < titles[-1]['t0'] + 2.5: continue
        on_b = any(s['line'] == 'B' and s['t0'] <= T < s['t1'] for s in shots)
        lines = [[big, 'BIG', 6.0, '#FFD54A']] + ([[small, 'ITA', 3.2, '#FFFFFF']] if small else [])
        titles.append(dict(t0=round(max(0, T - .05), 3), t1=round(min(total - .05, T + 2.9), 3), line='A', lines=lines, y_pct=20.0 if on_b else 62.0, bright=True))
        sfx.append(dict(file='SFX pop chu 02.wav', t=round(T, 3), vol=.16, dur=0.180091))
    for i in range(len(titles) - 1): titles[i]['t1'] = min(titles[i]['t1'], round(titles[i + 1]['t0'] - .1, 3))
    for ti in titles:   # giật zoom nhẹ ở từ khóa
        for sh in shots:
            x = ti['t0'] + .06
            if sh['line'] == 'A' and sh['t0'] + .25 < x < sh['t1'] - .3:
                k0, k1 = sh['keys'][0], sh['keys'][-1]; m = k0[1]
                sh['keys'] = [k0, [round(x - .001, 3), m] + k0[2:], [round(x + .09, 3), round(m * 1.08, 4)] + k0[2:], [k1[0], round(m * 1.1, 4)] + k1[2:]]; break
    sfx.insert(0, dict(file='SFX impact epic 01.wav', t=0.0, src_in=1.25, vol=.25, dur=5.144853))
    mus, mt = [], 0.0
    MF = ('Nhac nen 06 - Rising Sun.mp3', 91.742041) if 'academy' in path_of(jb['id']).lower() or 'đào tạo' in jb['name'].lower() else ('Nhac nen 05 - Sparta.mp3', 104.045714)
    while mt < total - .5:
        d = min(MF[1] - .1, total - mt); mus.append(dict(file=MF[0], dur=MF[1], src_in=0.0, t0=round(mt, 3), t1=round(mt + d, 3), fi=.3 if mt else 0.0, fo=1.2)); mt += d
    return dict(project=proj, out_dir=os.path.join(L.TMP, 'out'), asset_dir=adir, media=media, total=total, lines=[dict(id='A', t0=0.0, t1=total)],
                speech=speech, shots=shots, titles=titles, transitions=[], effects=[], music=mus, sfx=sorted(sfx, key=lambda x: x['t']), matte=[])

def engine():
    if os.path.exists(os.path.join(ENG, 'build.py')): return
    setup = lq("'%s' in parents and name='%s'" % (L.ROOT, SETUP_NAME))[0]['id']; z = lq("'%s' in parents and name='%s'" % (setup, ENG_NAME))[0]['id']
    os.makedirs(ENG, exist_ok=True); p = os.path.join(L.TMP, 'eng.zip'); open(p, 'wb').write(raw(z)); zipfile.ZipFile(p).extractall(ENG)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'fonttools'], capture_output=True)

# ---------------------------------------------------------------- 4) đưa project lên Drive + danh sách lối tắt
def list_file():
    setup = lq("'%s' in parents and name='%s'" % (L.ROOT, SETUP_NAME))[0]['id']
    return lq("'%s' in parents and name='%s'" % (setup, LIST_NAME))[0]['id']
def list_edit(add=(), remove=()):
    fid = list_file(); lines = [x.strip() for x in raw(fid).decode('utf-8-sig').splitlines() if x.strip()]
    lines = [x for x in lines if x not in remove] + [x for x in add if x not in lines]
    update(fid, ('\r\n'.join(lines) + '\r\n').encode('utf-8'), 'text/plain')
def publish(jb, sc, n):
    a0 = jb['A'][0]; host = a0['vid']['dir'] if len(jb['dirs']) > 1 and all(x['vid']['dir'] == a0['vid']['dir'] for x in jb['A']) else jb['id']
    proj = safe('CapCut - %s - %s' % (safe(jb['name'], 40), safe(sc.get('ten') or 'Video %d' % n, 50)), 110)
    rel = path_of(host) + '/' + proj; adir = DRV + '/' + rel + '/AI tải về'
    pl = build_plan(jb, sc, proj, adir)
    if not pl: log('  bỏ kịch bản quá ngắn:', proj); return None
    pp = os.path.join(L.TMP, 'plan_%d.json' % n); json.dump(pl, open(pp, 'w'), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(ENG, 'build.py'), pp], capture_output=True, text=True, timeout=600)
    od = os.path.join(pl['out_dir'], proj)
    if not os.path.exists(os.path.join(od, 'draft_content.json')): raise RuntimeError('dựng lỗi: ' + (r.stderr or r.stdout)[-300:])
    for old in lq("'%s' in parents and name='%s' and mimeType='%s'" % (host, proj.replace("'", "\\'"), L.FOLDER), 'id'):   # chỉ giữ 1 phiên bản
        list_edit(remove=[rel]); L.drive('files/' + old['id'], {'trashed': True}, method='PATCH')
    pf = mkdir(proj, host); af = mkdir('AI tải về', pf)
    for f in lq("'%s' in parents" % LIB, 'id,name'):
        if not f['name'].startswith(LIB_SKIP): L.drive('files/%s/copy' % f['id'], {'name': f['name'], 'parents': [af]}, params={'fields': 'id'})
    for fn in ('draft_content.json', 'draft_info.json', 'draft_meta_info.json'):
        put(fn, pf, open(os.path.join(od, fn), 'rb').read(), 'application/json')
    put('draft_cover.jpg', pf, base64.b64decode(a0['thumbs'][len(a0['thumbs']) // 2][1]), 'image/jpeg')
    list_edit(add=[rel])
    return dict(proj=proj, dur=pl['total'], url='https://drive.google.com/drive/folders/' + pf)

def edit(jb, key, models):
    t0 = time.time(); engine()
    scs = plan(jb, key, models); done = []
    log('  Gemini: %d kịch bản' % len(scs))
    for n, sc in enumerate(scs, 1):
        try:
            r = publish(jb, sc, n)
            if r: done.append(r); log('  ✓ %s (%.0fs) – %.1f phút' % (r['proj'], r['dur'], (time.time() - t0) / 60))
        except Exception as e: log('  ✗ kịch bản', n, e)
    L.mark(jb['id'], dungV=DV, dungN=len(done), dungT=int(time.time()), dungFail=None)
    if done:
        L.tsay('🎬 AI DỰNG XONG %d PROJECT CAPCUT\n📁 %s\n%s\n⏱ %.0f phút · mở CapCut là có (lối tắt tự vào máy)' % (
            len(done), path_of(jb['id']), '\n'.join('• %s (%d giây)' % (r['proj'], r['dur']) for r in done), (time.time() - t0) / 60))
    return done

# ---------------------------------------------------------------- vòng chạy: đọc trước 1 buổi trong lúc dựng buổi hiện tại
def pending():
    try: return len(scan())
    except Exception as e: log('AI dựng: không quét được', e); return 0
def run(key, models, until):
    if not key: log('AI dựng: không có khóa Gemini'); return
    q, busy = queue.Queue(maxsize=1), set()
    def reader():
        while time.time() < until - 20 * 60:
            try: J = [j for j in scan() if j['id'] not in busy]
            except Exception as e: log('AI dựng: quét lỗi', e); time.sleep(60); continue
            if not J: q.put(None); return
            jb = J[0]; busy.add(jb['id']); log('AI dựng – đọc:', jb['src'], '›', jb['name'], '(%d video)' % len(jb['vids']))
            try: q.put(read(jb))
            except Exception as e:
                log('  đọc lỗi:', e); L.mark(jb['id'], dungFail=int(jb['ap'].get('dungFail') or 0) + 1, dungErr=str(e)[:100])
        q.put(None)
    th = threading.Thread(target=reader, daemon=True); th.start()
    while True:
        jb = q.get()
        if jb is None: break
        try: edit(jb, key, models)
        except Exception as e:
            log('✗ AI dựng lỗi:', e); L.mark(jb['id'], dungFail=int(jb['ap'].get('dungFail') or 0) + 1, dungErr=str(e)[:100])
            L.tsay('❌ AI DỰNG LỖI\n📁 %s\n%s' % (jb['name'], str(e)[:300]))
