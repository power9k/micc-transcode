# AI DỰNG PROJECT CAPCUT (bản 1, 10/11/2026) – chạy trên máy GitHub cùng lượt với loc.py
# Mỗi buổi quay (thư mục con của "Source"), từ MỚI đến CŨ, buổi mới tải lên được ưu tiên ngay sau buổi đang làm:
#  1) ĐỌC: xem hình (khung chính, độ nét/rung) + chép lời có mốc từng chữ – đọc song song với bước dựng
#  2) GEMINI (theo QUY TẮC DỰNG của chủ): tự chia kịch bản (mỗi video < 2 phút) nếu không có file kịch bản,
#     chọn câu nói hay nhất (đủ ý, đúng diễn xuất), cảnh phụ khớp lời, chữ nhấn ý chính
#  3) DỰNG: bỏ ngập ngừng / ầm à, che vết cắt bằng giật zoom, cảnh phụ, chữ, nhạc, hiệu ứng âm thanh → draft CapCut
#  4) Đưa project vào thư mục buổi quay (1 phiên bản duy nhất) + thêm vào MICC media · Hệ thống (không xóa)/AI dựng CapCut/Danh sách project CapCut.txt (máy nhân viên tự có lối tắt)
import os, io, sys, json, time, re, math, threading, queue, zipfile, base64, subprocess, unicodedata, urllib.request, urllib.parse, urllib.error
import loc as L
import xem as X, nao as N   # bản nâng cấp: X = mắt + tai (khung hình, mặt, âm thanh, nhạc), N = bộ não Claude

DV = '12'
LV = '6'   # kiểu dựng: 2 = nhiều lớp (A-roll / B-roll / màu / chữ / nhạc / SFX)                                   # đổi số này = dựng lại mọi buổi quay
EXCL = set()   # 11/11 chiều: chủ cho thu hồi cả Center Avenue KB1/KB2 và để AI dựng lại (làm sau cùng)
SYS_NAME, CACHE_NAME, LIST_NAME, ENG_NAME, PROG_NAME = 'MICC media · Hệ thống (không xóa)', 'AI dựng CapCut', 'Danh sách project CapCut.txt', 'Bộ dựng AI.zip', 'Tiến độ AI dựng.txt'   # mọi thứ AI tự tạo: MICC media · Hệ thống (không xóa)/AI dựng CapCut – SETUP chỉ cho người dùng
_CD = []
def cache_dir():
    if not _CD:
        par = L.ROOT
        for nm in (SYS_NAME, CACHE_NAME):
            f = lq("'%s' in parents and name='%s' and mimeType='%s' and trashed=false" % (par, nm, L.FOLDER), 'id')
            par = f[0]['id'] if f else mkdir(nm, par)
        _CD.append(par)
    return _CD[0]
LIB = '1ZIROORo_epCYmpf55Q0reoT8gOfCwyEX'  # thư mục nhạc + hiệu ứng âm thanh + font mẫu (AI tải về của Center Avenue KB2)
LIB_SKIP = ('Phim ', 'Outro ')
DRV = 'G:/Drive của tôi/PHÒNG TRUYỀN THÔNG MICC'   # đường dẫn lúc dựng; công cụ đồng bộ trên từng máy đổi sang đúng ổ Drive của tài khoản tailieumkt trên máy đó
MROOT = re.compile(r'[A-Za-z]:(?:/|\\\\)+(?:Drive của tôi|My Drive)(?:/|\\\\)+PHÒNG TRUYỀN THÔNG MICC')
def to_m(b): return MROOT.sub('M:', unicodedata.normalize('NFC', b.decode('utf-8'))).encode('utf-8')
def migrate_m():   # project cũ (G:/Drive của tôi/...) → M:/... để máy nào mở cũng thấy file
    n = 0
    for nm in ('draft_content.json', 'draft_info.json'):
        for f in lq("name='%s' and fullText contains 'PHÒNG TRUYỀN THÔNG MICC' and trashed=false" % nm, 'id,name'):
            try:
                b = raw(f['id']); nb = to_m(b)
                if nb != b: update(f['id'], nb, 'application/json'); n += 1
            except Exception as e: log('  không đổi được đường dẫn', f['id'], e)
    if n: log('Đổi %d file project sang ổ M:' % n)
SKIPDIR = re.compile(r'^(capcut|lọc|loc\b|bộ nhớ đệm|ai tải về|_ai)', re.I)
ENG = os.path.join(L.TMP, 'eng')
_PL, _PF = [], [None]
def log(*a):   # ghi log + file tiến độ trên Drive (SETUP/AI dựng – tiến độ.txt) để theo dõi khi máy đang chạy
    L.log(*a)
    try:
        _PL.append(time.strftime('%H:%M:%S ', time.gmtime(time.time() + 7 * 3600)) + ' '.join(str(x) for x in a)); del _PL[:-60]
        if time.time() - (_PF[1:] or [0])[0] < 20 and not re.search(r'✓|✗|xong|lỗi', _PL[-1]): return   # ghi Drive tối đa 20 s/lần
        _PF[1:] = [time.time()]
        if not _PF[0]:
            cd = cache_dir(); f = lq("'%s' in parents and name='%s' and trashed=false" % (cd, PROG_NAME))
            _PF[0] = f[0]['id'] if f else put(PROG_NAME, cd, b' ', 'text/plain')['id']
        update(_PF[0], '\r\n'.join(_PL).encode('utf-8'), 'text/plain')
    except Exception: pass

def lq(q, f='id,name,mimeType,size,createdTime,parents,appProperties,videoMediaMetadata(width,height,durationMillis)'):
    for k in range(6):   # Drive báo "quá hạn mức" → chờ rồi thử lại, không bỏ cả lượt
        try: return L.listq(q + ' and trashed=false', f, L.corpora())
        except Exception as e:
            if k == 5 or not re.search(r'403|429|rate|5\d\d', str(e)): raise
            time.sleep(15 * (k + 1))
def kids(fid): return lq("'%s' in parents" % fid)
def get(fid, f='id,name,parents,appProperties'): return L.drive('files/' + fid, params={'fields': f})
def raw(fid, anon=False):   # file nhỏ hay đổi (danh sách, trạng thái, kịch bản) → luôn đọc bằng tài khoản (đường khách có thể trả bản cũ đã lưu tạm); anon=True chỉ cho file lớn không đổi (nhạc, video)
    if anon:
      try:
        with urllib.request.urlopen(urllib.request.Request(L.aurl(fid)), timeout=300) as r:
            if 'text/html' not in (r.headers.get('Content-Type') or ''): return r.read()
      except Exception: pass
    for t in dict.fromkeys([L.rtok(), L.tok()]):   # đọc bằng tài khoản 2 trước, lỗi thì tài khoản MICC
        try:
            with urllib.request.urlopen(urllib.request.Request(L.durl(fid), headers={'Authorization': 'Bearer ' + t}), timeout=300) as r: return r.read()
        except urllib.error.HTTPError as e:
            if t == L.tok(): raise
            L.log('  tài khoản 2 không đọc được file, dùng tài khoản MICC:', e.code)
def put(name, parent, data, mime):  # tải file nhỏ lên Drive (multipart), thử lại khi Drive báo quá hạn mức
    for k in range(4):
        try: return _put(name, parent, data, mime)
        except Exception as e:
            if k == 3 or not re.search(r'403|429|5\d\d|rate', str(e)): raise
            time.sleep(15 * (k + 1))
def _put(name, parent, data, mime):
    b = '----micc%d' % time.time()
    body = ('--%s\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n%s\r\n--%s\r\nContent-Type: %s\r\n\r\n' % (
        b, json.dumps({'name': name, 'parents': [parent]}), b, mime)).encode() + data + ('\r\n--%s--' % b).encode()
    return L.http(L.G + '/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id', body,
                  {'Authorization': 'Bearer ' + L.tok(), 'Content-Type': 'multipart/related; boundary=' + b})
def update(fid, data, mime):
    return L.http(L.G + '/upload/drive/v3/files/' + fid + '?uploadType=media&supportsAllDrives=true', data,
                  {'Authorization': 'Bearer ' + L.tok(), 'Content-Type': mime}, method='PATCH')
def mkdir(name, parent, ap=None): return L.drive('files', dict({'name': name, 'parents': [parent], 'mimeType': L.FOLDER}, **({'appProperties': ap} if ap else {})), params={'fields': 'id'})['id']
AI_ICON = '🤖'
def du_an(path):   # tên dự án = thư mục ngay trên SOURCE (bỏ ngày đầu tên, vd "20261030 Khai phá tư duy" → "Khai phá tư duy")
    sg = [x for x in path.split('/') if x]
    i = next((k for k, x in enumerate(sg) if re.match(r'^sources?$', L.norm1(x))), len(sg))
    nm = sg[i - 1] if i > 0 else (sg[-1] if sg else '')
    return re.sub(r'^\d{6,8}\s*[-_.]?\s*', '', nm).strip()
def full_name(path, ten):   # 🤖 Tên dự án - Nội dung (nội dung không lặp lại tên dự án)
    da = du_an(path); t = ten
    vs = set()
    for base in (da, re.sub(r'(?i)^vinhomes\s+', '', da)):
        w = base.split()
        for k in range(len(w), 1, -1): vs.add(' '.join(w[:k]))   # "Vinhomes King Park Bắc Ninh" → cả "Vinhomes King Park", "King Park"
    for v in sorted(vs, key=len, reverse=True):
        if v and len(v) > 3: t = re.sub(re.escape(v), '', t, flags=re.I)
    t = re.sub(r'\s{2,}', ' ', t).strip(' -–:,'); t = t[:1].upper() + t[1:]
    return '%s %s - %s' % (AI_ICON, da, t or ten)
def safe(s, k=70): return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|\n\r\t]+', ' ', str(s))).strip()[:k].strip()
def tsafe(s, k=40):   # chữ trên hình: giữ "/" (9/11, TRIỆU/M2); font không có ² → M2
    s = re.sub(r'[\\:*?"<>|\n\r\t]+', ' ', str(s or '')).replace('²', '2').replace('³', '3')
    s = re.sub(r'(?i)(triệu|tỷ|tỉ|nghìn|ngàn|tr)\s*/?\s*m2\b', lambda m: m.group(1) + '/m2', s)
    return re.sub(r'\s+', ' ', s).strip()[:k].strip()
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
    sids = {f['id'] for f in srcs}
    def has_src_anc(f, d=0):
        for p in f.get('parents') or []:
            if p in sids or (p in by and d < 40 and has_src_anc(by[p], d + 1)): return True
        return False
    srcs = [f for f in srcs if not has_src_anc(f)]   # thư mục source lồng trong source khác → thuộc source cha
    KB = re.compile(r'^(kịch bản|kich ban|kb)\s*\d', re.I)
    ok = lambda c: not SKIPDIR.match(nf(c['name'])) and (c.get('appProperties') or {}).get('dungP') != '1' and c['id'] not in EXCL
    jobs, now = [], time.time()
    for s in srcs:   # 1 thư mục SOURCE = 1 lượt: đọc HẾT mọi thư mục con, Claude nhìn tổng thể rồi chia các kịch bản (mỗi cái < 2 phút)
        ap = s.get('appProperties') or {}
        if ONLY and ONLY not in L.norm1(path_of(s['id'])): continue   # chạy thử bản nâng cấp trên 1 dự án trước
        if ap.get('dungV') == DV or (ap.get('dungFailV') == DV and int(ap.get('dungFail') or 0) >= 3): continue
        dirs, kbtop, dn, st, hitx = [], {}, {}, [(s, None)], False
        while st:
            d, top = st.pop(); dirs.append(d['id']); dn[d['id']] = nf(d['name'])
            hitx = hitx or any(c['id'] in EXCL for c in ch.get(d['id'], []))
            if top: kbtop[d['id']] = top
            for c in ch.get(d['id'], []):
                if ok(c): st.append((c, top or (c['id'] if KB.match(nf(c['name'])) else None)))
        vids, docs = [], []
        for d in dirs:
            for c in kids(d):
                if L.is_video(c) and not c['name'].lower().endswith('.lrf'): vids.append(dict(c, dir=d, broll=bool(kbtop) and d not in kbtop))
                elif c['mimeType'] in ('application/vnd.google-apps.document', 'text/plain') or c['name'].lower().endswith(('.docx', '.txt')): docs.append(c)
        if hitx and not kbtop: continue   # source có kịch bản chủ tự làm (Center Avenue KB1/KB2) mà không còn kịch bản nào khác
        if not [v for v in vids if not v['broll']]: continue
        last = max(L.ts(v['createdTime']) for v in vids)
        if now - last < L.SETTLE: continue   # còn đang tải lên
        jobs.append(dict(id=s['id'], name=nf(s['name']), src=nf(s['name']), dirs=dirs, ap=ap, pool=[], kbtop=kbtop, dn=dn, vids=vids, docs=docs, last=last))
    jobs.sort(key=lambda j: -j['last'])
    return jobs

# ---------------------------------------------------------------- 1) đọc source (song song với dựng)
_MEM, _ANA = {}, []   # kết quả đọc video: nhớ trong lượt + lưu Drive (MICC media · Hệ thống/AI dựng CapCut/Phân tích video) → video đã đọc KHÔNG đọc lại
def ana_dir():
    if not _ANA:
        f = lq("'%s' in parents and name='Phân tích video' and mimeType='%s'" % (cache_dir(), L.FOLDER), 'id')
        _ANA.append(f[0]['id'] if f else mkdir('Phân tích video', cache_dir()))
        _ANA.append({x['name']: x['id'] for x in lq("'%s' in parents" % _ANA[0], 'id,name')})
    return _ANA
def jdef(o):
    if hasattr(o, 'tolist'): return o.tolist()
    try: return float(o)
    except Exception: return str(o)
def read(jb):
    t0 = time.time(); A = []
    vids = sorted(jb['vids'], key=lambda v: v['name'])
    from concurrent.futures import ThreadPoolExecutor
    try: ad, idx = ana_dir()
    except Exception as e: ad, idx = None, {}; log('  không mở được kho phân tích:', e)
    def one(iv): return read_video(iv[0], iv[1], len(vids), ad, idx, t0)
    with ThreadPoolExecutor(3) as ex: A = [a for a in ex.map(one, enumerate(vids)) if a]
    return read_tail(jb, vids, A, ad, idx, t0)

def ana_name(v): return '%s_%s%s_v2.json' % (v['id'], v.get('size') or 0, '' if v.get('broll') else '_loi')   # v2 = có tờ ảnh mọi khung chính + mặt + nhãn âm thanh
def xem_name(v): return '%s_%s_xem.json' % (v['id'], v.get('size') or 0)
def hong_name(v): return '%s_%s_hong.json' % (v['id'], v.get('size') or 0)   # video hỏng / không đọc được → bỏ qua, không đọc lại
def read_video(i, v, nv, ad, idx, t0):
        br = bool(v.get('broll')); nm = ana_name(v)
        if hong_name(v) in idx: return None
        a = _MEM.get(nm)
        if a is None and nm in idx:
            try: a = json.loads(raw(idx[nm]).decode('utf-8'))
            except Exception: a = None
        if a is None:
            try: a = L.analyze(i + 1, dict(id=v['id'], name=v['name'], size=int(v.get('size') or 0), dur=float((v.get('videoMediaMetadata') or {}).get('durationMillis') or 0) / 1000))
            except Exception as e: log('  bỏ video đọc lỗi:', v['name'], e); return None
            a['segs'] = [] if br else L.transcribe(a['wav'])
            a['see'] = X.perceive(a, a['segs']); a['wav'] = bool(a.get('wav'))
            a = json.loads(json.dumps(a, default=jdef))
            if ad:
                try: put(nm, ad, json.dumps(a, ensure_ascii=False).encode('utf-8'), 'application/json')
                except Exception as e: log('  không lưu được phân tích', v['name'], e)
            log('  đọc video %d/%d: %s (%.1f phút từ đầu)' % (i + 1, nv, v['name'], (time.time() - t0) / 60))
        _MEM[nm] = a
        return dict(a, i=i + 1, vid=v)

def read_tail(jb, vids, A, ad, idx, t0):
    if not A: raise RuntimeError('không đọc được video nào')
    log('  %d video, %d video đã đọc từ trước (dùng lại, không đọc lại)' % (len(A), sum(1 for v in vids if any(k.startswith(v['id'] + '_') for k in idx))))
    gb = sum(int(v.get('size') or 0) for v in vids) / 1e9
    log('  đọc xong %s: %d video, %.1f GB trong %.1f phút' % (jb['name'], len(A), gb, (time.time() - t0) / 60))
    newly = len(A) - sum(1 for v in vids if any(k.startswith(v['id'] + '_') for k in idx))
    if newly > 0:
     try: L.tsay('📖 AI ĐÃ ĐỌC XONG SOURCE\n📁 %s\n🎬 %d video · %.1f GB · %.0f phút đọc\n➡️ Bắt đầu chia kịch bản + dựng project' % (path_of(jb['id']), len(A), gb, (time.time() - t0) / 60))
     except Exception as e: log('  không báo được:', e)   # chỉ báo khi thật sự có video mới đọc (đọc lại từ bộ nhớ thì im)
    jb['A'] = A; jb['ad'], jb['idx'] = ad, idx; look(jb, ad, idx); return jb

def look(jb, ad, idx):   # Claude Sonnet XEM tờ ảnh mẫu (mọi khung chính) của từng video → nhật ký hình; lưu Drive, video đã xem không xem lại
    need = []
    for a in jb['A']:
        nm = '%s_%s_xem.json' % (a['vid']['id'], a['vid'].get('size') or 0)
        if nm in _MEM: a['vlog'] = _MEM[nm]; continue
        if nm in idx:
            try: a['vlog'] = _MEM[nm] = json.loads(raw(idx[nm]).decode('utf-8')); continue
            except Exception: pass
        if (a.get('see') or {}).get('sheets'): need.append((a, nm))
    if not need: return
    t0 = time.time(); bat, n = [], 0
    def go(bat):
        r = N.see([(a['i'], a['name'], a['dur'], not a['vid'].get('broll'), a['see']['sheets'][:30]) for a, _ in bat], log=log)
        for a, nm in bat:
            if a['i'] in r:
                a['vlog'] = _MEM[nm] = r[a['i']]
                if ad:
                    try: put(nm, ad, json.dumps(r[a['i']], ensure_ascii=False).encode('utf-8'), 'application/json')
                    except Exception as e: log('  không lưu nhật ký hình', a['name'], e)
    for a, nm in need:   # gom ~24 tờ ảnh / lượt gọi để đỡ tốn token khởi động
        k = min(30, len(a['see']['sheets']))
        if bat and n + k > 24: go(bat); bat, n = [], 0
        bat.append((a, nm)); n += k
    if bat: go(bat)
    log('  Claude đã xem %d video (%.1f phút)' % (sum(1 for a, _ in need if a.get('vlog')), (time.time() - t0) / 60))

# ---------------------------------------------------------------- 2) Claude chia kịch bản + chọn cảnh
RULES = '''QUY TẮC DỰNG CỦA CHỦ (bắt buộc):
- MỖI VIDEO PHẢI CÓ ĐẦU CÓ ĐUÔI: câu mở hút (hook) + thân + câu KẾT rõ ràng (chốt ý / kêu gọi bình luận, liên hệ, theo dõi). Không có câu kết hợp ở đoạn đó thì lấy câu kết phù hợp ở chỗ khác trong source – ĐƯỢC PHÉP dùng lại câu đã dùng ở kịch bản khác.
- MỖI VIDEO 1 NHÂN VẬT CHÍNH: A-roll chỉ lấy lời của đúng người dẫn chính của video đó, không chen người khác (trừ khi kịch bản là hỏi – đáp).
- LỖI HAY BỊ KIỂM DUYỆT LOẠI – tránh ngay từ đầu: chữ nhấn cụt nghĩa ("SẮP CÓ", "VỪA Ở", "CÓ MUỐN", "RẤT ĐÁNG" → phải là "SẮP CÓ DỰ ÁN LỚN", "VỪA Ở VỪA KINH DOANH"); chữ đọc như khẳng định sai ý người nói; câu A-roll bị cụt / thiếu con số (chọn trọn câu, kể cả số liệu); cảnh phụ mờ, rung, trắng xóa, logo, chữ in sẵn; mở đầu người nói nhìn lệch máy / ngập ngừng (chọn câu hút nhất làm câu đầu); kết cụt (phải có câu chốt / kêu gọi).
- Mỗi kịch bản = 1 video DƯỚI 2 PHÚT (tổng A-roll 45–110 giây). Buổi quay dài (đào tạo, hội thảo) → tách thành nhiều tập, mỗi tập 1 ý trọn vẹn, có câu mở hút (hook) và kết.
- Nếu có file kịch bản: theo đúng kịch bản. Nếu thư mục con đặt tên "Kịch bản 1/2" thì mỗi thư mục con là 1 kịch bản.
- A-roll: chỉ lấy câu người nói ĐÚNG lời thoại, nói trôi chảy, diễn xuất tốt (không đứng nhẩm, không nói lại, không nhăn mặt). Mỗi câu nói lại nhiều lần → chọn 1 bản hay nhất. Giữ TRỌN câu, không cắt giữa câu.
- Cảnh phụ (B-roll) phải KHỚP lời đang nói. Không dùng cảnh có người đang nói câu khác. Mỗi cảnh dùng 1 lần, không lặp cảnh giống nhau.
- Không cố nhét cảnh: ít cảnh đẹp thì dùng ít.
- Đã có NHẬT KÝ HÌNH (Claude xem mọi khung hình chính) + nhãn âm thanh cho từng video: A-roll tránh đoạn ghi "ngập ngừng / quay đi / ra hiệu cắt / mờ / rung"; cảnh phụ chọn đoạn điểm ≥ 7, máy chạy mượt, nội dung KHỚP lời; tránh đoạn có gió/ù, ồn nếu lấy tiếng.
- Câu đầu = câu hút (hook) mạnh nhất; câu cuối = kết trọn ý / kêu gọi.
- Chữ: KHÔNG chạy phụ đề theo lời. Cứ 1–3 giây phải có 1 cụm chữ nhấn (video 60 s ≈ 25–35 cụm), hiện đúng lúc người nói nói chữ đó ("tu"); chọn chữ ĐẮT (số liệu, tên riêng, tính từ mạnh, lợi ích), không chép cả câu: "big" = TỪ KHÓA viết hoa ≤ 3 từ (số liệu, tên dự án, lợi ích), "small" = 1 dòng phụ ≤ 6 từ. Đúng chính tả tiếng Việt, trọn nghĩa.'''
SYS = '''Bạn là editor video ngắn (TikTok/Reels dọc 9:16) chuyên nghiệp của team truyền thông MICC (bất động sản + đào tạo).
Bạn nhận toàn bộ source của 1 buổi quay: lời thoại có mốc thời gian, chất lượng hình, ảnh khung hình. Hãy lên kế hoạch DỰNG các video ngắn.
''' + RULES + '''
Trả về JSON: {"scripts":[{"ten":"nội dung video, 3–7 chữ, không ghi CapCut / Kịch bản / số thứ tự","aroll":["C12","C13","C20",...],"broll":[{"video":<số # cảnh phụ>,"s":giây,"e":giây,"cau":"C13"}],"titles":[{"cau":"C12","tu":"đúng 1–3 chữ người nói trong câu đó (chép y nguyên)","big":"TỪ KHÓA (chữ đậm chính, ≤3 từ)","small":"câu dẫn viết tay ngắn ≤5 từ đặt TRÊN chữ chính, vd \"Khi kết nối tốt hơn\" / big \"DÒNG TIỀN\" (có thể để trống)"}]}]}
- Lời thoại đã được máy chia sẵn thành CÂU có mã (C1, C2, …). "aroll" = DANH SÁCH MÃ CÂU theo đúng thứ tự phát (KHÔNG ghi giây – máy tự lấy mốc chính xác). Mỗi câu nói lại nhiều lần → chọn 1 mã hay nhất. Tổng độ dài các câu chọn 45–110 giây (độ dài mỗi câu ghi trong ngoặc).
- broll "cau" = mã câu A-roll mà cảnh phụ bắt đầu che hình (tiếng vẫn là A-roll); "s","e" = giây trong video cảnh phụ, mỗi cảnh 1.5–3.5 giây.
- titles "cau" = mã câu có từ khóa đó.
- Không có kịch bản dựng được (source hỏng / chỉ thử máy) → {"scripts":[]}.'''
_RX = []
def rules_extra():   # quy tắc chủ dặn thêm (file "Quy tắc dựng AI.md" trong AI dựng CapCut – sửa file là AI làm theo, không cần sửa code)
    if not _RX:
        try:
            f = lq("'%s' in parents and name='Quy tắc dựng AI.md' and trashed=false" % cache_dir(), 'id')
            _RX.append(('\n\nQUY TẮC CHỦ DẶN THÊM (bắt buộc):\n' + raw(f[0]['id']).decode('utf-8')[:9000]) if f else '')
        except Exception as e: log('  không đọc được Quy tắc dựng AI.md', e); _RX.append('')
    return _RX[0]
def doc_text(jb):
    out = []
    for d in jb['docs'][:3]:
        try:
            if d['mimeType'] == 'application/vnd.google-apps.document':
                req = urllib.request.Request(L.G + '/drive/v3/files/%s/export?mimeType=text/plain' % d['id'], headers={'Authorization': 'Bearer ' + L.rtok()})
                with urllib.request.urlopen(req, timeout=120) as r: out.append('FILE KỊCH BẢN "%s":\n%s' % (d['name'], r.read().decode('utf-8', 'replace')[:12000]))
            elif d['name'].lower().endswith('.txt'): out.append('FILE KỊCH BẢN "%s":\n%s' % (d['name'], raw(d['id']).decode('utf-8', 'replace')[:12000]))
        except Exception as e: log('  không đọc được file kịch bản', d['name'], e)
    return '\n\n'.join(out)
# ---------------------------------------------------------------- Gemini Pro qua Gemini CLI (đăng nhập tài khoản có gói Pro/Ultra, chìa khóa khóa hóa trên Drive)
_CLI = []
def cli_ready():
    if _CLI: return _CLI[0]
    ok = False
    try:
        env = os.environ.get('GEMINI_CLI_CREDS', '').strip()   # cách 2: chủ tự dán nội dung oauth_creds.json vào GitHub secret GEMINI_CLI_CREDS
        if env:
            gd = os.path.expanduser('~/.gemini'); os.makedirs(gd, exist_ok=True)
            open(os.path.join(gd, 'oauth_creds.json'), 'w').write(env)
            json.dump({'security': {'auth': {'selectedType': 'oauth-personal'}}, 'selectedAuthType': 'oauth-personal'}, open(os.path.join(gd, 'settings.json'), 'w'))
            if not subprocess.run('command -v gemini', shell=True, capture_output=True).stdout:
                subprocess.run('npm install -g @google/gemini-cli >/dev/null 2>&1', shell=True, timeout=300)
            ok = bool(subprocess.run('command -v gemini', shell=True, capture_output=True).stdout)
            log('  Gemini Pro (GitHub secret):', 'sẵn sàng' if ok else 'không cài được'); _CLI.append(ok); return ok
        f = lq("'%s' in parents and name='Khoa Gemini.bin'" % cache_dir(), 'id')
        if f:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'cryptography'], capture_output=True)
            from cryptography.hazmat.primitives import serialization, hashes, padding as P
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            b = raw(f[0]['id']); assert b[:4] == b'MGC1'
            n = int.from_bytes(b[4:6], 'big'); ek, iv, ct = b[6:6 + n], b[6 + n:22 + n], b[22 + n:]
            pk = serialization.load_der_private_key(base64.b64decode(re.search(r"GEMINI_CLI_PRIV\s*=\s*'([^']+)'", L.cfg()['src']).group(1)), None)
            k = pk.decrypt(ek, padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None))
            d = Cipher(algorithms.AES(k), modes.CBC(iv)).decryptor(); u = P.PKCS7(128).unpadder()
            cred = u.update(d.update(ct) + d.finalize()) + u.finalize()
            gd = os.path.expanduser('~/.gemini'); os.makedirs(gd, exist_ok=True)
            open(os.path.join(gd, 'oauth_creds.json'), 'wb').write(cred)
            json.dump({'security': {'auth': {'selectedType': 'oauth-personal'}}, 'selectedAuthType': 'oauth-personal'}, open(os.path.join(gd, 'settings.json'), 'w'))
            if not subprocess.run('command -v gemini', shell=True, capture_output=True).stdout:
                subprocess.run('npm install -g @google/gemini-cli >/dev/null 2>&1', shell=True, timeout=300)
            ok = bool(subprocess.run('command -v gemini', shell=True, capture_output=True).stdout)
            log('  Gemini Pro (tài khoản đã kết nối):', 'sẵn sàng' if ok else 'không cài được')
    except Exception as e: log('  không dùng được Gemini Pro đã kết nối:', e)
    _CLI.append(ok); return ok
def cli_plan(parts):
    if not cli_ready(): return None
    import tempfile
    d = tempfile.mkdtemp(dir=L.TMP); txt, refs = [SYS, ''], []
    for p in parts:
        if 'text' in p: txt.append(p['text'])
        elif 'inline_data' in p and len(refs) < 60:
            fn = 'h%d.jpg' % len(refs); open(os.path.join(d, fn), 'wb').write(base64.b64decode(p['inline_data']['data'])); refs.append(fn); txt.append('(ảnh %s)' % fn)
    open(os.path.join(d, 'yeucau.txt'), 'w', encoding='utf-8').write('\n'.join(txt))
    q = 'Đọc yêu cầu trong @yeucau.txt, xem các ảnh ' + ' '.join('@' + r for r in refs) + ' rồi làm đúng yêu cầu. CHỈ trả về JSON, không giải thích.'
    for args in (['--output-format', 'json'], []):
        try:
            r = subprocess.run(['gemini', '-p', q] + args, cwd=d, capture_output=True, text=True, timeout=900)
            out = r.stdout.strip()
            try: out = json.loads(out).get('response', out)
            except Exception: pass
            m = re.search(r'\{.*\}', out, re.S)
            if m:
                sc = json.loads(m.group(0)).get('scripts')
                if sc is not None: log('  Gemini Pro (tài khoản) lên kế hoạch: %d kịch bản' % len(sc)); return sc
            log('  Gemini Pro (tài khoản) chưa trả JSON:', (r.stderr or out)[-200:])
        except Exception as e: log('  Gemini Pro (tài khoản) lỗi:', e)
    return None
# ---------------------------------------------------------------- Claude Code chạy không người bấm, dùng gói Claude Max (không tốn tiền API)
ClaudeWait = N.ClaudeWait
_CL = []
def claude_ready():
    if _CL: return _CL[0]
    ok = False
    if os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '').strip():
        if not subprocess.run('command -v claude', shell=True, capture_output=True).stdout:
            subprocess.run('npm install -g @anthropic-ai/claude-code >/dev/null 2>&1', shell=True, timeout=300)
        ok = bool(subprocess.run('command -v claude', shell=True, capture_output=True).stdout)
        log('  Claude (gói Max):', 'sẵn sàng' if ok else 'không cài được')
    _CL.append(ok); return ok
def claude_plan(parts):
    if not claude_ready(): return None
    import tempfile
    d = tempfile.mkdtemp(dir=L.TMP); txt, refs, nb = [SYS, ''], [], 0
    for p in parts:   # lời thoại + mô tả đưa thẳng vào câu hỏi (stdin); ảnh để file cho Claude tự mở (ưu tiên ảnh cảnh phụ, tối đa 30)
        if 'text' in p: txt.append(p['text']); nb = 1 if 'KHO CẢNH PHỤ' in p['text'] else (0 if p['text'].startswith('VIDEO') else nb)
        elif 'inline_data' in p and len(refs) < 30 and (nb or len(refs) < 12):
            fn = 'h%d.jpg' % len(refs); open(os.path.join(d, fn), 'wb').write(base64.b64decode(p['inline_data']['data'])); refs.append(fn); txt.append('(ảnh: %s)' % fn)
    body = '\n'.join(txt)
    q = ('Bạn là editor video. Toàn bộ yêu cầu + dữ liệu buổi quay nằm ở nội dung đầu vào. Dùng công cụ Read mở các ảnh h*.jpg trong thư mục hiện tại khi cần nhìn cảnh '
         '(nhất là ảnh cảnh phụ để ghép đúng lời). Câu trả lời CUỐI CÙNG chỉ là 1 khối JSON {"scripts":[...]} đúng khung đã nêu, không giải thích gì thêm.')
    for k in range(2):
        try:
            r = subprocess.run(['claude', '-p', q, '--output-format', 'json', '--allowedTools', 'Read'], input=body,
                               cwd=d, capture_output=True, text=True, timeout=1500)
            out = r.stdout.strip()
            try: out = json.loads(out).get('result', out)
            except Exception: pass
            m = re.search(r'\{.*\}', out or '', re.S)
            if m:
                try:
                    sc = json.loads(m.group(0)).get('scripts')
                    if sc is not None: log('  Claude lên kế hoạch: %d kịch bản' % len(sc)); return sc
                except Exception as e: log('  Claude trả JSON hỏng:', e)
            log('  Claude chưa trả JSON:', (r.stderr or out or '')[-300:])
        except Exception as e: log('  Claude lỗi:', e)
    return None
def faceless(a):   # bản thu tiếng (không thấy người nói) → phải phủ kín cảnh phụ
    fc = (a.get('see') or {}).get('faces'); kt = a.get('kt') or []
    if fc is None or len(kt) < 3 or len(fc) >= .2 * len(kt): return False
    dn = (a.get('vlog') or {}).get('doan') or []   # mặt nhỏ / quay xa YuNet có thể sót → hỏi thêm nhật ký hình của Claude
    ppl = sum(1 for x in dn if re.search(r'(?i)người|nói|dẫn|mc|cô gái|chàng trai|anh |chị |đứng|cầm mic', '%s %s' % (x.get('noi_dung', ''), x.get('canh', ''))))
    return not (dn and ppl >= .3 * len(dn))

def codes(jb):   # mã câu C1, C2… (cùng thứ tự với lúc lên kế hoạch) – cần cả khi dựng lại kịch bản đã lưu
    C = jb['C'] = {}
    for a in jb['A']:
        if a['vid'].get('broll'): continue
        for sg in a['segs']: C['C%d' % (len(C) + 1)] = (a['i'], float(sg['s']), float(sg['e']))
    return C

def plan(jb, key, models, extra=''):
    parts = [{'text': '⚠ TÊN RIÊNG: lời thoại do máy nghe nên hay sai tên riêng (vd "Kinh Bắc" thực ra là "King Park"). Tên dự án / địa danh CHUẨN lấy theo tên thư mục: %s. Chữ trên hình, tên video, dòng phụ phải viết ĐÚNG tên chuẩn, đúng chính tả – không chép nguyên lỗi của máy nghe; "tu" vẫn chép đúng như lời thoại (để bắt đúng lúc nói).\n\n' % path_of(jb['id']) + extra + 'Kênh / dự án: %s\nBuổi quay: %s\nCó %d video.\n%s' % (path_of(jb['id']), jb['name'], len(jb['A']), doc_text(jb) or '(không có file kịch bản – tự phân tích)') + ('\nSource có các thư mục con "Kịch bản N": MỖI thư mục Kịch bản = đúng 1 video (1 script), A-roll lấy từ chính thư mục đó; thư mục khác = kho cảnh phụ dùng chung.' if jb.get('kbtop') else '\nTự phân tích toàn bộ source để chia các kịch bản, mỗi kịch bản 1 video dưới 2 phút.')}]
    C = jb['C'] = {}
    for a in jb['A']:
        head = '[thư mục: %s] ' % (jb.get('dn') or {}).get(a['vid'].get('dir'), '') + L.summary(a).split('\nLời thoại:')[0]
        br_ = a['vid'].get('broll') or not a.get('segs')
        head += '\n' + N.vlog_text(a.get('vlog'), k=8 if br_ else 40) + ('' if br_ else '\n' + N.sound_text((a.get('see') or {}).get('sound')))   # cảnh phụ: tóm gọn 8 đoạn đẹp nhất để kịch bản không quá dài (source lớn vẫn chất lượng như source nhỏ)
        if not a['vid'].get('broll') and faceless(a): head += '\n⚠ VIDEO NÀY KHÔNG THẤY MẶT NGƯỜI NÓI (chỉ là bản thu tiếng) → chỉ lấy tiếng, mọi câu của video này phải có broll phủ kín (máy sẽ tự phủ cảnh phụ).'   # Claude đã XEM mọi khung hình + nghe âm thanh
        if a['vid'].get('broll'):
            parts.append({'text': '[KHO CẢNH PHỤ DÙNG CHUNG – chỉ dùng làm broll, KHÔNG làm aroll, không lấy tiếng]\n' + head})
            continue
        ln = []
        for sg in a['segs']:
            k = 'C%d' % (len(C) + 1); C[k] = (a['i'], float(sg['s']), float(sg['e'])); ln.append('%s (%.1fs) %s' % (k, sg['e'] - sg['s'], sg['t'].strip()))
        parts.append({'text': head + '\nCÁC CÂU NÓI:\n' + ('\n'.join(ln)[:9000] or '(không có lời)')})
    body = {'systemInstruction': {'parts': [{'text': SYS}]}, 'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'temperature': .3, 'maxOutputTokens': 30000, 'responseMimeType': 'application/json'}}
    j = N.ask_json('\n\n'.join(p['text'] for p in parts if 'text' in p) + '\n\nTrả đúng 1 khối JSON {"scripts":[...]} theo khung đã nêu.', model='opus', key='scripts', sys_p=SYS + rules_extra(), log=log)
    if j is not None: log('  Claude Opus lên kế hoạch: %d kịch bản' % len(j['scripts'])); return j['scripts']
    r = None   # (cách gọi cũ claude_plan bỏ: tốn token khung Claude Code + đọc ảnh từng lượt)
    if r is not None: return r  # 1) Claude (gói Claude Max của chủ, mã CLAUDE_CODE_OAUTH_TOKEN) – đọc lời + khung hình, chọn câu, viết chữ
    if r is not None: return r
    raise ClaudeWait('Claude chưa trả lời được (có thể đang hết hạn mức) – dừng, đợi lượt sau')   # chủ dặn: chỉ dùng bộ não Claude, hết hạn mức thì đợi, KHÔNG tự chọn theo luật
    last = ''
    for rnd in range(3):
        for m in models:
            try:
                j = L.http(L.GEM + 'models/' + m + ':generateContent', body, {'x-goog-api-key': key}, timeout=600)
                txt = ''.join(p.get('text', '') for p in ((j.get('candidates') or [{}])[0].get('content') or {}).get('parts', []))
                return json.loads(re.sub(r'^```(json)?|```$', '', txt.strip())).get('scripts') or []
            except Exception as e: last = '%s: %s' % (m, e); log('  Gemini lỗi:', last)
        time.sleep(20 * (rnd + 1))
    log('  Gemini hỏng hết (' + last + ') → tự chọn theo luật để vẫn ra project')
    return rule_plan(jb)
def rule_plan(jb):   # lớp dự phòng không cần AI: lấy câu theo thứ tự quay, câu nói lại thì giữ lần sau cùng, chữ nhấn = số liệu / từ dài
    import difflib
    C = jb.get('C') or {}
    if not C: return []
    crew = re.compile(r'(?i)\b(ba hai một|3 2 1|chuẩn bị|bắt đầu|cắt|ok rồi|được chưa|lại nhé|quay lại)\b')
    items = [(k, C[k]) for k in sorted(C, key=lambda x: int(x[1:]))]
    A = {a['i']: a for a in jb['A']}
    def txt(c): a = A[c[0]]; return ' '.join(w[2] for w in words(a, c[1], c[2])).strip()
    keep = []
    for k, c in items:
        t = txt(c)
        if c[2] - c[1] < 1.0 or len(t.split()) < 3 or crew.search(t): continue
        if keep and difflib.SequenceMatcher(None, keep[-1][2], t).ratio() > .55: keep[-1] = (k, c, t); continue   # nói lại → giữ lần sau
        keep.append((k, c, t))
    ar, tot = [], 0.0
    for k, c, t in keep:
        if tot > 100: break
        ar.append((k, c, t)); tot += c[2] - c[1]
    pool = [a for a in jb['A'] if a['vid'].get('broll')]
    titles, broll, bi = [], [], 0
    for j, (k, c, t) in enumerate(ar):
        ws = t.split()
        cand = [w for w in ws if re.search(r'\d', w)] or sorted(ws, key=len, reverse=True)[:2]
        for w in cand[:2]:
            i = ws.index(w); big = ' '.join(ws[i:i + 2]) if not re.search(r'\d', w) else ' '.join(ws[max(0, i - 1):i + 2])
            titles.append({'cau': k, 'tu': w, 'big': big, 'small': ''})
        if pool and j % 2 == 1:
            b = pool[bi % len(pool)]; bi += 1; s0 = min(2.0, max(0, b['dur'] - 3.5))
            broll.append({'video': b['i'], 's': s0, 'e': s0 + 2.6, 'cau': k})
    if tot < 20: return []
    return [{'ten': ' '.join(ar[0][2].split()[:6]), 'aroll': [x[0] for x in ar], 'broll': broll, 'titles': titles}]

# ---------------------------------------------------------------- 3) dựng → plan cho engine
CW, CH = 1080, 1920
def s0(a): w, h = a.get('w') or 1080, a.get('h') or 1920; return (w / h) / (CW / CH) if w / h > CW / CH + .01 else 1.0
def words(a, s, e): return [w for sg in a['segs'] for w in sg['w'] if w[0] >= s - .05 and w[1] <= e + .05]
BADW = re.compile(r'(?i)trắng|đen kịt|mờ|nhòe|rung|lóa|logo|chữ in|text|tiêu đề|fade|chuyển cảnh|màn hình trống|trống trơn|tay che|lỗi|hỏng|bị cắt|cận (tay|áo|ngực|cằm|cổ|vai|bụng|chân)|ngực|cằm|cổ áo|vạt áo|không thấy mặt|che mặt|nửa mặt|mất đầu|cây che|lá che|khuất')
def clean_seg(a, s0_, e0_):   # đo thật trên khung hình: bỏ đoạn trắng xóa / đen / phẳng
    try:
        import numpy as _np
        for t_ in (s0_ + .1, (s0_ + e0_) / 2, e0_ - .1):
            im = N._tile(a, t_)
            if im is None: continue
            g = _np.asarray(im.convert('L'), dtype=float)
            if g.mean() > 215 or g.mean() < 25 or g.std() < 18: return False
    except Exception: pass
    return True
def seg_ok(a, s0_, e0_):   # đoạn cảnh phụ đạt: Claude chấm ≥ 6, không mô tả lỗi, khung hình không trắng / đen
    for x in ((a.get('vlog') or {}).get('doan') or []):
        if min(e0_, float(x.get('e', 0))) - max(s0_, float(x.get('s', 0))) > .3:
            if float(x.get('diem') or 6) < 6 or BADW.search('%s %s' % (x.get('chat_luong', ''), x.get('noi_dung', ''))): return False
    return clean_seg(a, s0_, e0_)
def best_seg(a, near=0.0, dmin=1.6):   # đoạn đẹp nhất của video (gần giây Claude chọn)
    d = [x for x in ((a.get('vlog') or {}).get('doan') or []) if float(x.get('e', 0)) - float(x.get('s', 0)) >= dmin]
    d.sort(key=lambda x: (-float(x.get('diem') or 0), abs(float(x['s']) - near)))
    for x in d:
        if seg_ok(a, float(x['s']), min(float(x['e']), float(x['s']) + 3)): return float(x['s'])
    return None

def kat(keys, t):   # khung máy [t, zoom, u, v, xoay] tại thời điểm t (nội suy giữa các khóa)
    if t <= keys[0][0]: return list(keys[0])
    for a_, b_ in zip(keys, keys[1:]):
        if a_[0] <= t <= b_[0]:
            f = (t - a_[0]) / max(1e-6, b_[0] - a_[0]); return [t] + [x + (y - x) * f for x, y in zip(a_[1:], b_[1:])]
    return list(keys[-1])
def punch2(keys, T, cap=9.0):   # giật zoom KỊCH TÍNH (giật 2 nhịp) cho cú nhấn mạnh / số liệu
    kv = kat(keys, T); z = kv[1]; c = lambda v: round(min(v, cap), 4)
    if c(z * 1.16) - z < .06: return keys
    return [k for k in keys if k[0] < T - .002] + [[round(T - .001, 3)] + kv[1:], [round(T + .06, 3), c(z * 1.10)] + kv[2:], [round(T + .14, 3), c(z * 1.04)] + kv[2:],
            [round(T + .22, 3), c(z * 1.16)] + kv[2:]] + [[k[0], c(k[1] * 1.17)] + list(k[2:]) for k in keys if k[0] > T + .22]
def punch(keys, T, k1=1.14, k2=1.16, cap=9.0):   # giật zoom tại T mà vẫn giữ đường bám mặt; không vượt mức cận tối đa của cảnh
    kv = kat(keys, T); z1 = min(kv[1] * k1, cap)
    if z1 - kv[1] < .05: return keys   # đã cận sẵn → không giật thêm (tránh cận cằm)
    return [k for k in keys if k[0] < T - .002] + [[round(T - .001, 3)] + kv[1:], [round(T + .08, 3), round(z1, 4)] + kv[2:]] + \
           [[k[0], round(min(k[1] * k2, cap), 4)] + list(k[2:]) for k in keys if k[0] > T + .08]

def tighten(a, s, e):   # bỏ ngập ngừng: cắt ĐÚNG khoảng lặng giữa 2 từ, không cắt vào chữ
    W0 = [w for w in words(a, s, e) if L.norm(w[2]) not in L.FILL and L.norm(w[2]) not in ('ạ', 'ơi à', 'ờ thì')]
    W = [w for k_, w in enumerate(W0) if not (k_ + 1 < len(W0) and L.norm(W0[k_ + 1][2]) == L.norm(w[2]) and W0[k_ + 1][0] - w[1] < .6)]   # nói lắp "thì thì", "là là" → bỏ chữ đầu
    if not W: return [(s, e)]
    iv = []
    for w in W:   # khoảng ngập ngừng > 0,3 s giữa 2 chữ (thường là "ầm / ừm" máy nghe không ghi) → cắt bỏ cho mượt
        if iv and w[0] - iv[-1][1] <= .3: iv[-1][1] = w[1]
        else: iv.append([w[0], w[1]])
    allw = sorted((w for sg in a['segs'] for w in sg['w']), key=lambda w: w[0])
    pe = max([w[1] for w in allw if w[1] <= iv[0][0] + .01 and w[0] < iv[0][0] - .01] or [-9])   # chữ ngay TRƯỚC đoạn (câu khác) → đệm không được lấn vào
    ns = min([w[0] for w in allw if w[0] >= iv[-1][1] - .01 and w[1] > iv[-1][1] + .01] or [1e9])   # chữ ngay SAU đoạn
    out = []
    for k, (x, y) in enumerate(iv):
        lo = iv[k - 1][1] + .03 if k else max(s - .2, pe + .03)
        hi = iv[k + 1][0] - .03 if k + 1 < len(iv) else min(e + .3, ns - .03)
        x2, y2 = max(lo, x - (.12 if k == 0 else .07)), min(hi, y + (.2 if k + 1 == len(iv) else .1))   # chỗ cắt giữa câu đệm ngắn để không dính tiếng ầm ừ
        if y2 - x2 > .3: out.append((max(0.0, x2), min(y2, a['dur'] - .05)))
    return out
def grade_of(a):   # đo màu gốc từng cảnh → thông số lớp Điều chỉnh để ra ĐÚNG màu mẫu chủ gửi
    if a.get('mau'): return a['mau']   # Claude đã XEM khung hình video này và đặt thông số
    try:
        import numpy as np, io
        from PIL import Image
        px = []
        for t, b in a.get('thumbs', [])[:6]:
            im = Image.open(io.BytesIO(base64.b64decode(b))).convert('RGB').resize((96, 170)); px.append(np.asarray(im, dtype=np.float32) / 255.0)
        if not px: return {}
        x = np.concatenate([p.reshape(-1, 3) for p in px]); R, G, B = x[:, 0], x[:, 1], x[:, 2]
        Y = .2126 * R + .7152 * G + .0722 * B; m, sd = float(Y.mean()), float(Y.std())
        hi, lo = float((Y > .92).mean()), float((Y < .06).mean())
        sat = float((x.max(1) - x.min(1)).mean()); cast = float(R.mean() - B.mean()); gm = float(G.mean() - (R.mean() + B.mean()) / 2)
        c = lambda v, a_, b_: round(max(a_, min(b_, v)), 3)
        # MÀU MẪU CỦA CHỦ (ảnh mẫu 10/11 + 2 video mẫu BĐS): sáng trong, trắng sạch, ấm nhẹ, xanh lá tươi, da hồng hào, tương phản vừa
        TG = dict(m=.50, sd=.25, sat=.16, cast=.045, gm=.015)   # 11/11 chiều: rõ hơn, điện ảnh hơn, bão hòa hơn – vẫn tươi sáng   # + 5 ảnh mẫu 11/11: sáng thoáng, trắng sạch gần trung tính, da ấm, cỏ cây tươi, tương phản mềm, bóng không bệt
        g = dict(brightness=c((TG['m'] - m) * 1.2, -.3, .35),
                 contrast=c((TG['sd'] - sd) * 2.0, -.2, .45),
                 saturation=c((TG['sat'] - sat) * 3.0, -.3, .4),
                 temperature=c((TG['cast'] - cast) * 1.8, -.35, .35),
                 tone=c(-(gm - TG['gm']) * 2.0, -.25, .25),
                 highlight=c(-hi * 3 - .04, -.4, 0),
                 shadow=c((lo - .03) * 2.0 + .04, -.05, .3))   # nâng nhẹ vùng tối cho thoáng, sang
        return g
    except Exception as e: log('  không đo được màu', a.get('name'), e); return {}
FX_TR = [('Pull in', '6724226861666144779'), ('Glare II', '6952697917563998722'), ('Flash', '6987208055511323137'), ('Pull out', '6724226338418332167')]
BMOVES = [((1.0, .5, .5, 0.0), (1.09, .5, .5, 0.0)), ((1.1, .5, .5, 0.0), (1.0, .5, .5, 0.0)), ((1.08, .44, .5, 0.0), (1.08, .56, .5, 0.0)),
          ((1.08, .56, .5, 0.0), (1.08, .44, .5, 0.0)), ((1.05, .5, .5, -1.2), (1.1, .5, .5, 1.2)), ((1.0, .5, .56, 0.0), (1.08, .5, .46, 0.0))]
def build_plan(jb, sc, proj, adir, music=None, mmap=None):
    parts = music if isinstance(music, list) else None
    mmap = mmap or {}; beats = sorted((mmap.get('kicks') or []) + (mmap.get('snares') or [])) or (mmap.get('beats') or [])
    A = {a['i']: a for a in jb['A']}; media, shots, speech, titles, sfx, trans, fx = {}, [], [], [], [], [], []
    def key(a):
        k = 'V%d' % a['i']
        if k not in media:
            media[k] = dict(path=DRV + '/' + path_of(a['vid']['dir']) + '/' + nf(a['name']), dur=a['dur'], w=a.get('w') or 1080, h=a.get('h') or 1920,
                            kind='video', has_audio=bool(a.get('wav')), name=nf(a['name']), S0=s0(a), grade=grade_of(a))
        return k
    C = jb.get('C') or {}
    def conv(x): return C.get(str(x).strip().upper()) if isinstance(x, str) else None
    def vid(x): m = re.search(r'\d+', str(x)); return int(m.group()) if m else 0
    if any(isinstance(x, str) for x in sc.get('aroll', [])):
        sc = dict(sc); sc['aroll'] = [{'video': c[0], 's': c[1], 'e': c[2]} if c else {'video': 0, 's': 0, 'e': 0} for c in map(conv, sc.get('aroll', []))]   # giữ số thứ tự để Claude kiểm duyệt bỏ đúng câu
        sc['broll'] = [dict(b, luc=[conv(b.get('cau'))[0], conv(b.get('cau'))[1]]) if conv(b.get('cau')) else dict(b, video=0) for b in sc.get('broll', [])]   # giữ đúng số thứ tự (Claude kiểm duyệt gọi theo số)
        sc['titles'] = [dict(t, video=conv(t.get('cau'))[0], s=conv(t.get('cau'))[1], e=conv(t.get('cau'))[2]) if conv(t.get('cau')) else dict(t, video=0) for t in sc.get('titles', [])]
    # ---- A-roll: câu nói nối liền, cắt ở khoảng lặng; mỗi CÂU 1 cỡ khung (rộng / cận) để nhảy cỡ che vết cắt
    t, pieces, why, n_sent, lastw = 0.0, [], {}, 0, []
    for ai, it in enumerate(sc.get('aroll', [])):
        a = A.get(vid(it.get('video', 0))); s, e = float(it.get('s', 0)), float(it.get('e', 0))
        if not a: why['sai số video'] = why.get('sai số video', 0) + 1; continue
        if a['vid'].get('broll'): why['chọn nhầm cảnh phụ'] = why.get('chọn nhầm cảnh phụ', 0) + 1; continue
        if e - s < .6: why['đoạn quá ngắn'] = why.get('đoạn quá ngắn', 0) + 1; continue
        e = min(e, a['dur'] - .05); base = 1.0 if n_sent % 2 == 0 else 1.2; n_sent += 1
        for j, (x, y) in enumerate(tighten(a, s, e)):
            wl = [w for w in words(a, x, y) if L.norm(w[2]) not in L.FILL]
            for kk in (3, 2, 1):   # câu sau mở đầu bằng đúng chữ cuối câu trước ("…quá cao" / "cao… vì thế") → gọt bỏ chữ lặp
                if len(wl) > kk and len(lastw) >= kk and [L.norm(w[2]) for w in wl[:kk]] == lastw[-kk:]:
                    x = max(x, min(wl[kk - 1][1] + .03, wl[kk][0] - .03)); wl = wl[kk:]; break
            if y - x < .3 or not wl: continue
            lastw = (lastw + [L.norm(w[2]) for w in wl])[-6:]
            d = y - x; k = key(a); m = base if j % 2 == 0 else round(base * 1.1, 3)
            f0, f1 = N.face_span(a, x, x + min(d, 1.5)), N.face_span(a, max(x, y - 1.5), y)   # bám mặt người nói (YuNet theo từng khung chính)
            fr0 = f0 or f1
            fs_ = [f_ for f_ in (a.get('see') or {}).get('faces') or [] if x - .3 <= f_[0] <= y + .3]
            nk_ = len([t_ for t_ in (a.get('kt') or []) if x - .3 <= t_ <= y + .3]) or 1
            if fr0 and not (len(fs_) >= max(1, .5 * nk_) and .05 <= fr0[3] <= .4 and .12 <= fr0[1] <= .62 and .15 <= fr0[0] <= .85): fr0 = f0 = f1 = None   # mặt không chắc (nhận nhầm) → không bám, không zoom, giữ khung rộng
            # ZOOM CÓ CHỦ ĐÍCH: không cận quá (mặt tối đa ~22 % chiều cao khung → không cắt cằm); không thấy mặt thì không zoom mạnh
            zc = round(max(1.0, min(1.22, .2 / fr0[3])), 3) if fr0 and fr0[3] > .02 else 1.0   # không thấy mặt chắc chắn → không zoom; tối đa 1,22 (không cắt cằm / ngực)
            m = min(m, zc); m1 = round(min(zc, m * (1 + min(.05, .015 * d))), 4)
            uv = lambda f, mm: (round(min(.8, max(.2, f[0])), 3), round(min(.55, max(.3, f[1] + .1 / mm)), 3)) if f else (.5, .42)   # mặt ở ~1/3 trên khung; khung không bao giờ trượt xuống ngực
            u0, v0 = uv(f0, m); u1, v1 = uv(f1 or f0, m1)
            kp = [[round(t, 3), m, u0, v0, 0.0]]
            su, sv = u0, v0
            for fr in sorted(f_ for f_ in (a.get('see') or {}).get('faces') or [] if x + .3 < f_[0] < y - .3 and fr0 and .12 <= f_[2] <= .62   # TRACKING: khung bám theo người nói di chuyển
                             and abs(f_[1] - fr0[0]) < .18 and abs(f_[2] - fr0[1]) < .18 and .6 < f_[4] / max(fr0[3], 1e-3) < 1.7):   # bỏ mặt nhận nhầm (lệch xa / to nhỏ bất thường)
                mm = m + (m1 - m) * (fr[0] - x) / max(d, 1e-6); fu, fv = uv(fr[1:], mm)
                su, sv = su + (fu - su) * .6, sv + (fv - sv) * .6   # làm mượt, không giật theo từng khung
                if abs(su - kp[-1][2]) > .01 or abs(sv - kp[-1][3]) > .01: kp.append([round(t + fr[0] - x, 3), round(mm, 4), round(su, 3), round(sv, 3), 0.0])
            kp.append([round(t + d, 3), m1, u1 if len(kp) == 1 else su, v1 if len(kp) == 1 else sv, 0.0])
            mv_ = (n_sent + j) % 4   # chuyển động máy kiểu điện ảnh, đổi liên tục: đẩy vào / lia ngang / xoay vòng nhẹ (orbit) / dolly lùi
            for kk_ in kp:
                fr_ = (kk_[0] - t) / max(d, 1e-6)
                if mv_ == 1: kk_[2] = round(kk_[2] + (fr_ - .5) * .06 * (1 if n_sent % 2 else -1), 3)
                elif mv_ == 2 and fr0: kk_[4] = round((-1.0 + 2.0 * fr_) * (1 if n_sent % 2 else -1), 3); kk_[1] = round(max(kk_[1], 1.04), 4)   # xoay cần phóng nhẹ để không lộ viền
                elif mv_ == 3: kk_[1] = round(max(1.0, min(zc, kk_[1] * (1.05 - .05 * fr_))), 4)
            shots.append(dict(media=k, src=round(x, 3), t0=round(t, 3), t1=round(t + d, 3), line='A', face=f0 or f1, keys=kp, punch_abs=[], zc=zc))
            speech.append(dict(media=k, src_in=round(x, 3), t0=round(t, 3), t1=round(t + d, 3), vol=1.0))
            pieces.append((a['i'], x, y, t, ai)); t += d
        if t > 118: break
    for w_ in sc.get('_wide') or []:   # kiểm duyệt yêu cầu khung rộng (khung cắt mặt / quá cận) → về khung rộng giữa, không zoom, không giật
        for sh in shots:
            if sh['line'] == 'A' and min(sh['t1'], float(w_[1])) - max(sh['t0'], float(w_[0])) > .05:
                sh['keys'] = [[sh['t0'], 1.0, .5, .42, 0.0], [sh['t1'], 1.0, .5, .42, 0.0]]; sh['face'] = None; sh['zc'] = 1.0
    if t < 15: log('  A-roll chỉ %.0fs (%d đoạn Gemini chọn, bỏ: %s)' % (t, len(sc.get('aroll', [])), why or 'không')); return None
    total = round(t, 3)
    def tl(vi, st):
        for i, x, y, t0, *_ in pieces:
            if i == vi and x - .05 <= st <= y + .05: return t0 + max(0, min(y, st) - x)
        return None
    # ---- cảnh phụ: mỗi cảnh 1 kiểu chuyển động máy khác nhau; ≤1 cảnh / 5 s; 3–4 chuyển cảnh có hiệu ứng ở chỗ đổi ý
    used, lastB, mv = set(), -9.0, 0
    for bi, b in enumerate(sc.get('broll', [])):
        a = A.get(vid(b.get('video', 0))); at = b.get('luc') or [0, 0]
        if not a or a['i'] in used: continue
        T = tl(vid(at[0]), float(at[1])) if isinstance(at, list) and len(at) == 2 else None
        if T is None or T < 1.5 or T - lastB < 5.0: continue
        cut = min((p[3] for p in pieces if abs(p[3] - T) < .8), key=lambda c: abs(c - T), default=None)   # bám vào chỗ cắt / ngắt câu gần nhất
        if cut is not None and cut >= 1.5: T = cut
        cuts_ = [p[3] for p in pieces] + [p[3] + p[2] - p[1] for p in pieces]
        def on_beat(x):   # đổi cảnh đúng phách nhạc (kick / snare), nhưng không để lại mẩu hình < 0.35 s cạnh chỗ cắt
            y = N.snap(x, beats, .3) if beats else x
            return y if all(abs(y - c) < .01 or abs(y - c) >= .35 for c in cuts_) else x
        T = on_beat(T)
        s, e = float(b.get('s', 0)), float(b.get('e', 0)); d = min(3.0, max(1.6, e - s), total - T - .3)
        if not seg_ok(a, s, s + max(d, 1.3)):   # đoạn Claude chọn bị mờ / trắng / lỗi → lấy đoạn đẹp nhất của chính video đó, không có thì bỏ
            s2 = best_seg(a, s)
            if s2 is None: continue
            s, e = s2, s2 + 3
        e2 = on_beat(T + d); d = e2 - T if 1.3 <= e2 - T <= 3.3 and e2 < total - .3 else d   # cảnh phụ kết thúc cũng rơi vào phách
        if d < 1.3 or s + d > a['dur']: continue
        k = key(a); used.add(a['i']); lastB = T + d; new = []
        for sh in shots:
            if sh['t1'] <= T or sh['t0'] >= T + d: new.append(sh); continue
            if sh['t0'] < T - .05: new.append(dict(sh, t1=round(T, 3), keys=[[sh['t0']] + sh['keys'][0][1:], [round(T, 3)] + sh['keys'][-1][1:]]))
            if sh['t1'] > T + d + .05: new.append(dict(sh, src=round(sh['src'] + T + d - sh['t0'], 3), t0=round(T + d, 3), keys=[[round(T + d, 3)] + sh['keys'][0][1:], [sh['t1']] + sh['keys'][-1][1:]]))
        k0, k1 = BMOVES[mv % len(BMOVES)]; mv += 1
        new.append(dict(media=k, src=round(s, 3), t0=round(T, 3), t1=round(T + d, 3), line='B', bi=bi, keys=[[round(T, 3)] + list(k0), [round(T + d, 3)] + list(k1)], punch_abs=[]))
        shots = sorted(new, key=lambda x: x['t0'])
        if len(trans) < 4 and (not trans or T - trans[-1]['at'] > 10):
            nm, eid = FX_TR[len(trans) % len(FX_TR)]
            trans.append(dict(name=nm, effect_id=eid, at=round(T, 3), dur_s=.4))
            sfx.append(dict(file='SFX whoosh mem.wav', t=max(0, round(T - .25, 3)), vol=.3, dur=0.58))
            if nm == 'Glare II' and not fx: fx.append(dict(preset='effect_lens_flare.json', t0=round(T, 3), dur_s=.6))
    # ---- bản thu tiếng không thấy người: phủ kín cảnh phụ (mỗi cảnh ≤3 s, đổi video liên tục, ưu tiên đoạn Claude chấm điểm cao)
    keyA = {'V%d' % a['i']: a for a in A.values()}
    poolB = [A[vid(b.get('video', 0))] for b in sc.get('broll', []) if A.get(vid(b.get('video', 0)))]
    poolB += [a for a in A.values() if (a['vid'].get('broll') or not a.get('segs')) and a not in poolB]
    def segs_of(a):
        BADW = re.compile(r'(?i)trắng|đen|mờ|nhòe|rung|lóa|logo|chữ|text|tiêu đề|fade|chuyển cảnh|màn hình|trống')
        d = [x for x in ((a.get('vlog') or {}).get('doan') or []) if float(x.get('e', 0)) - float(x.get('s', 0)) >= 1.4
             and float(x.get('diem') or 6) >= 6 and not BADW.search('%s %s' % (x.get('chat_luong', ''), x.get('noi_dung', '')))]
        d.sort(key=lambda x: -float(x.get('diem') or 0))
        out_ = [(float(x['s']), float(x['e'])) for x in d] or ([] if (a.get('vlog') or {}).get('doan') else [(min(1.0, a['dur'] / 4), a['dur'] - .2)])
        bad_ = [(int(v), float(g)) for v, g in sc.get('_bad') or []]
        return [g for g in out_ if clean(a, g[0], min(g[1], g[0] + 2.6)) and not any(v == a['i'] and g[0] - .5 <= x_ <= g[1] + .5 for v, x_ in bad_)]
    def clean(a, s0_, e0_):   # đo thật trên khung hình: bỏ đoạn trắng xóa / đen / phẳng (logo mờ dần, màn hình trống)
        try:
            import numpy as _np
            for t_ in (s0_ + .1, (s0_ + e0_) / 2, e0_ - .1):
                im = N._tile(a, t_)
                if im is None: continue
                g = _np.asarray(im.convert('L'), dtype=float)
                if g.mean() > 215 or g.mean() < 25 or g.std() < 18: return False
        except Exception: pass
        return True
    cur = {id(a): 0 for a in poolB}; pi = [0]
    def next_b(dmin):
        for _ in range(len(poolB)):
            a = poolB[pi[0] % len(poolB)]; pi[0] += 1; sg = segs_of(a); j = cur[id(a)]
            if j < len(sg) and sg[j][1] - sg[j][0] >= dmin: cur[id(a)] += 1; return a, sg[j]
        if any(cur.values()):   # hết đoạn mới → dùng lại từ đầu (source ít cảnh phụ), vẫn hơn để lộ cảnh không người
            for k_ in cur: cur[k_] = 0
            return next_b(dmin)
        return None
    if poolB:
        out = []
        for sh in shots:
            a = keyA.get(sh['media'])
            if sh['line'] != 'A' or not a or not faceless(a) or sh['t1'] - sh['t0'] < .5: out.append(sh); continue
            t = sh['t0']
            while t < sh['t1'] - .05:
                d = min(2.6, sh['t1'] - t)
                if sh['t1'] - (t + d) < .9: d = sh['t1'] - t
                nb = next_b(min(d, 1.4))
                if not nb: out.append(dict(sh, t0=round(t, 3), keys=[[round(t, 3)] + sh['keys'][0][1:], [sh['t1']] + sh['keys'][-1][1:]])); break
                b, (bs, be) = nb; d = min(d, be - bs) if be - bs > .9 else d
                k0, k1 = BMOVES[mv % len(BMOVES)]; mv += 1
                out.append(dict(media=key(b), src=round(bs, 3), t0=round(t, 3), t1=round(t + d, 3), line='B', bi=-1, phu=1, keys=[[round(t, 3)] + list(k0), [round(t + d, 3)] + list(k1)], punch_abs=[]))
                t += d
        shots = sorted(out, key=lambda x: x['t0'])
    # mẩu hình < 0.6 s (thừa ra sau khi chèn cảnh phụ) → nhập vào cảnh liền trước, không để giật hình
    out = []
    for sh in shots:
        if out and sh['t1'] - sh['t0'] < .6:
            pv = out[-1]; pv['t1'] = sh['t1']; pv['keys'] = pv['keys'][:-1] + [[sh['t1']] + pv['keys'][-1][1:]]; continue
        if not out and sh['t1'] - sh['t0'] < .6 and len(shots) > 1:
            nx = shots[1]; d_ = nx['t0'] - sh['t0']; nx['src'] = round(max(0, nx['src'] - d_), 3); nx['t0'] = sh['t0']; nx['keys'][0][0] = sh['t0']; continue
        out.append(sh)
    shots = out
    # khớp chuyển cảnh với chỗ cắt thật sau khi chèn
    cuts = {round(s_['t1'], 3) for s_ in shots}
    trans = [x for x in trans if round(x['at'], 3) in cuts]
    # ---- chữ nhấn: hiện ĐÚNG lúc nói từ khóa (mốc từng chữ của Whisper), 1 cụm / 4–7 s
    def norm(x): return L.norm(x) if hasattr(L, 'norm') else x.lower()
    STY = [('#FFD54A', '#FFFFFF', 6.0), ('#FFFFFF', '#FFD54A', 5.4), ('#7FE3FF', '#FFFFFF', 5.6), ('#FFE08A', None, 6.4), ('#FFFFFF', None, 5.0), ('#FF6B5E', '#FFFFFF', 6.2)]
    def t_of(ti):
        vi = vid(ti.get('video', 0)); a = A.get(vi)
        if not a: return None
        s, e = float(ti.get('s', ti.get('t', 0))), float(ti.get('e', ti.get('t', 0)) or 0) or float(ti.get('t', 0)) + 4
        tu = [norm(w) for w in str(ti.get('tu') or ti.get('big') or '').split() if w.strip()]
        W = words(a, s - .1, e + .1); st = None
        if tu:
            for j, w in enumerate(W):
                if norm(w[2]) == tu[0] and (len(tu) == 1 or j + 1 >= len(W) or norm(W[j + 1][2]) == tu[1]): st = w[0]; break
            if st is None: st = next((w[0] for w in W if norm(w[2]) in tu), None)
        T = tl(vi, st if st is not None else s + .1)
        return None if T is None or T > total - .8 else T
    cand = sorted(((t_of(ti), si, ti) for si, ti in enumerate(sc.get('titles', [])[:80])), key=lambda x: x[0] if x[0] is not None else 1e9)
    lastp = -9.0
    for T, si, ti in cand:   # xếp theo GIÂY TRÊN TIMELINE (không theo giây gốc của từng video)
        if T is None: continue
        if titles and T < titles[-1]['t0'] + 1.2: continue   # chữ dày: 1 cụm mỗi 1–3 s
        big = tsafe(ti.get('big', ''), 32).upper(); small = tsafe(ti.get('small', ''), 48)
        if not big: continue
        bw = [L.norm(w) for w in big.split()]
        BAD = {'và', 'của', 'là', 'thì', 'mà', 'với', 'cho', 'các', 'những', 'một', 'này', 'đó', 'để', 'từ', 'đến', 'ở', 'tại', 'ra', 'vào', 'nhưng', 'cũng', 'rất', 'được', 'có', 'như', 'khi', 'thể'}
        HEAD_BAD = {'và', 'nhưng', 'mà', 'thì', 'là', 'của', 'với'}; TAIL_BAD = HEAD_BAD | {'các', 'những', 'một', 'cho', 'được', 'rất', 'cũng', 'như', 'khi'}
        if not bw or bw[0] in HEAD_BAD or bw[-1] in TAIL_BAD: log('  bỏ chữ không trọn nghĩa:', big); continue   # vd "NINH VÀ"; vẫn giữ "TỪ 7 TỶ", "MUA ĐỂ Ở"
        n = len(titles); num = bool(re.search(r'\d', big))
        on_b = any(x['line'] == 'B' and x['t0'] <= T < x['t1'] for x in shots)
        # chữ 2 tầng (theo bộ mẫu BĐS): dòng viết tay dẫn ý + dòng chữ đậm chính, tối đa 2 dòng; màu nhấn đổi theo cụm, quầng sáng mềm
        COL = ['#FFD54A', '#7FE3FF', '#FF9A6B', '#FFFFFF', '#FFB3D1']
        c1 = '#FFD54A' if num else COL[n % len(COL)]
        main = 'BEB' if n % 3 != 2 or re.search(r'[!+%/:()"\'#*&]', big) else 'BIG'   # font Nexa bản dùng thử không có các ký tự này (hiện ô "Việt hóa bởi…")
        lead = small if small and len(small.split()) <= 6 else ''
        if lead and n % 2 == 0: lines = [[lead[:1].upper() + lead[1:], 'SCR', 3.6, '#FFFFFF'], [big, main, 7.6 if main == 'BEB' else 6.2, c1]]
        else: lines = [[big, main, 8.2 if main == 'BEB' else 6.6, c1]]
        y = (19.0 + (n % 3) * 4) if on_b else (68.0 + (n % 2) * 3)   # cảnh người nói: chữ dưới ngực, không đè mặt; vùng an toàn TikTok ≤75 %
        if ti.get('y'): y = max(12.0, min(80.0, float(ti['y'])))   # vị trí Claude kiểm duyệt yêu cầu
        titles.append(dict(t0=round(max(0, T - .04), 3), t1=round(min(total - .05, T + 2.2), 3), line='A', lines=lines, y_pct=y, bright=False, anim=n, si=si, yfix=bool(ti.get('y')), onb=on_b))
        if num: sfx.append(dict(file='SFX tit thong tin.wav', t=round(max(0, T - .02), 3), vol=.2, dur=0.34))   # tiếng "tít" khi thông tin / số liệu hiện
        elif n % 3 == 0: sfx.append(dict(file='SFX pop chu 02.wav', t=round(max(0, T - .02), 3), vol=.12, dur=0.180091))
        if (num or n % 3 == 0) and T - lastp >= 4.0:   # giật zoom có chủ đích: số liệu / từ khóa mạnh, cách nhau ≥ 4 s
            for sh in shots:   # giật zoom đúng lúc nói từ khóa (cảnh người nói)
                if sh['line'] == 'A' and sh.get('face') and sh['t0'] + .2 < T < sh['t1'] - .35:
                    T = N.snap(T, beats, .12) if beats else T   # giật zoom trùng phách nếu phách ở rất gần từ khóa
                    sh['keys'] = (punch2 if num else punch)(sh['keys'], T, cap=min(1.3, sh.get('zc', 1.0) * 1.12)); lastp = T; break
    # (bỏ phần tự thêm chữ từ lời nói: chủ phản ánh ra cụm vô nghĩa như "NINH VÀ", "TRƯỜNG SỐNG" – chữ chỉ lấy từ AI, có kiểm tra trọn nghĩa)
    titles.sort(key=lambda z: z['t0'])
    for n, z in enumerate(titles): z['anim'] = n
    # ---- chữ né mặt: tính vị trí mặt trên khung 9:16 (sau zoom) lúc chữ hiện → chữ đè mặt thì dời xuống dưới cằm / lên trên đầu
    AK = {key(a): a for a in A.values() if 'V%d' % a['i'] in media}
    def face_canvas(T):
        sh = next((x for x in shots if x['t0'] <= T < x['t1'] and x['line'] != 'A'), None) or next((x for x in shots if x['t0'] <= T < x['t1']), None)
        if not sh: return None
        a = AK.get(sh['media']); f = N.face_at(a, sh['src'] + T - sh['t0']) if a else None
        if not f: return None
        k = kat(sh['keys'], T); m = k[1]; lim = max(0.0, (m - 1) / (2 * m)); v = max(.5 - lim, min(.5 + lim, k[3])); u = max(.5 - lim, min(.5 + lim, k[2]))   # engine giới hạn khung không lộ viền
        return (.5 + (f[1] - f[3] / 2 - v) * m) * 100, (.5 + (f[1] + f[3] / 2 - v) * m) * 100, (.5 + (f[0] - u) * m) * 100
    for z in titles:
        hh = sum(l[2] for l in z['lines']) * .75 + 2
        if not z.get('yfix') and not z.get('onb'):   # BỐ CỤC: khung đã crop mà trên đầu còn trống → đặt chữ vào khoảng trống đó, không đè lên người
            fcs = [f_ for f_ in (face_canvas(z['t0'] + .05), face_canvas((z['t0'] + z['t1']) / 2)) if f_]
            if fcs:
                head = min(f_[0] - (f_[1] - f_[0]) * .5 for f_ in fcs)   # đỉnh đầu (tính cả tóc)
                if head - 14 >= hh + 3: z['y_pct'] = round(max(14 + hh / 2, head - hh / 2 - 3), 1); z['tren'] = 1; continue
        for T in (z['t0'] + .05, (z['t0'] + z['t1']) / 2):
            fc = face_canvas(T)
            if not fc or fc[1] < z['y_pct'] - hh / 2 - 1 or fc[0] > z['y_pct'] + hh / 2 + 1: continue
            below, above = fc[1] + hh / 2 + 3, fc[0] - hh / 2 - 3
            z['y_pct'] = round(below if below <= 76 else (above if above >= 14 else 76), 1); z['ne_mat'] = 1; break
    # ---- TRACKING CHỮ: chữ trôi theo người / cảnh (như gắn vào cảnh) + phóng nhẹ cho sống động
    for n_, z in enumerate(titles):
        pts, base = [], None
        tt = z['t0']
        while tt <= z['t1'] + 1e-3:
            fc = face_canvas(tt)
            if fc and base is None: base = fc
            dx = ((fc[2] - base[2]) / 100 * .35) if fc and base else 0.0
            dy = (((fc[0] + fc[1]) / 2 - (base[0] + base[1]) / 2) / 100 * .35) if fc and base else 0.0
            pts.append([round(tt, 3), round(dx, 4), round(dy, 4), round(1 + .05 * (tt - z['t0']) / max(.3, z['t1'] - z['t0']), 4)])
            tt += .4
        if n_ % 3 == 1: pts = [[p_[0], round(p_[1] + .012 * (p_[0] - z['t0']), 4), p_[2], p_[3]] for p_ in pts]   # xen kẽ: chữ trượt ngang nhẹ
        z['trk'] = pts
    # ---- điểm dồn của nhạc (drop) → giật zoom mạnh đúng lúc nhạc dồn
    for dp in (mmap.get('drops') or [])[:2]:
        if 2 < dp < total - 2:
            sh = next((x for x in shots if x['t0'] + .2 < dp < x['t1'] - .3 and x['line'] == 'A'), None)
            if sh and sh.get('face'): sh['keys'] = punch(sh['keys'], dp, 1.15, 1.16, cap=min(1.3, sh.get('zc', 1.0) * 1.12))
    for i in range(len(titles) - 1): titles[i]['t1'] = min(titles[i]['t1'], round(titles[i + 1]['t0'] - .08, 3))
    sfx.insert(0, dict(file='SFX impact epic 01.wav', t=0.0, src_in=1.25, vol=.2, dur=5.144853))
    # ---- nhạc nền: mỗi project 1 bài riêng (chọn ở publish), lặp nếu ngắn
    if parts:   # nhạc mix: mỗi bài 1 đoạn, đổi bài đúng chỗ ngắt câu, chồng 0,8 s cho chuyển mượt; nhịp cắt cảnh theo bài đang phát
        cutsA = sorted({round(p[3], 3) for p in pieces} | {total})
        bounds = [0.0] + [min(cutsA, key=lambda c: abs(c - p_['f0'] * total)) for p_ in parts[1:]] + [total]
        mus, beats = [], []
        for k_, p_ in enumerate(parts):
            t0_, t1_ = bounds[k_], bounds[k_ + 1]
            if t1_ - t0_ < 1: continue
            tt_, src_ = t0_, p_['src']
            while tt_ < t1_ - .3:
                d_ = min(p_['dur'] - src_ - .1, t1_ - tt_ + (.8 if k_ + 1 < len(parts) else 0), total - tt_)
                if d_ < .5:
                    if src_ == 0.0 or total - tt_ < .5 or t1_ - tt_ < .5: break
                    src_ = 0.0; continue
                mus.append(dict(file=p_['nm'], dur=p_['dur'], src_in=round(src_, 3), t0=round(tt_, 3), t1=round(tt_ + d_, 3), fi=.8 if tt_ > 0 else 0.0, fo=.8 if tt_ + d_ < total - .1 else 1.5))
                mm_ = p_['mm'] or {}
                beats += [tt_ + b - src_ for b in (mm_.get('kicks') or []) + (mm_.get('snares') or []) if src_ <= b <= src_ + d_]
                tt_ += d_ - (.8 if tt_ + d_ < t1_ else 0); src_ = 0.0
        beats.sort()
    MF = music if not parts else ('x', 1)
    MF = MF or (('Nhac nen 06 - Rising Sun.mp3', 91.742041) if 'academy' in path_of(jb['id']).lower() or 'đào tạo' in jb['name'].lower() else ('Nhac nen 05 - Sparta.mp3', 104.045714))
    mus, mt = (mus, total) if parts else ([], 0.0)
    while mt < total - .5:
        d = min(MF[1] - .1, total - mt); mus.append(dict(file=MF[0], dur=MF[1], src_in=0.0, t0=round(mt, 3), t1=round(mt + d, 3), fi=.3 if mt else 0.0, fo=1.5)); mt += d
    # ---- tách lớp như người dựng: A-roll liền mạch dưới cùng (kể cả dưới cảnh phụ), cảnh phụ lớp trên
    ashots, bshots, lastk = [], [], [1.0, .5, .42, 0.0]
    for sh in shots:
        if sh['line'] == 'A': ashots.append(sh); lastk = list(sh['keys'][-1][1:]); continue
        bshots.append(sh)
        for sp in speech:
            s_, e_ = max(sh['t0'], sp['t0']), min(sh['t1'], sp['t1'])
            if e_ - s_ > .005:
                ashots.append(dict(media=sp['media'], src=round(sp['src_in'] + s_ - sp['t0'], 3), t0=round(s_, 3), t1=round(e_, 3), line='A',
                                   keys=[[round(s_, 3)] + lastk, [round(e_, 3)] + lastk], punch_abs=[]))
    ashots.sort(key=lambda x: x['t0'])
    # KHUNG NỔI: cứ khoảng 1/3 cảnh phụ (dài ≥ 2 s, video người nói có mặt) → người nói thu nhỏ ở góc dưới, cảnh phụ to phía sau
    pips, kb_ = [], 0
    for b in bshots:
        if b['t1'] - b['t0'] < 2.0: continue
        kb_ += 1
        if True: continue   # tạm tắt khung nổi: chủ báo ghép xấu (11/11)
        sp = next((x for x in speech if x['t0'] <= b['t0'] + .05 and x['t1'] >= b['t1'] - .05), None)
        a_ = AK.get(sp['media']) if sp else None
        if not a_ or faceless(a_): continue
        f_ = N.face_span(a_, sp['src_in'] + b['t0'] - sp['t0'], sp['src_in'] + b['t1'] - sp['t0'])
        if not f_: continue
        side = 1 if kb_ % 2 else -1; md_ = media.get(sp['media']) or {}
        Sw = md_.get('S0', 1.0) if (md_.get('w') or 1) > (md_.get('h') or 1) else 1.0
        sc_ = round(min(.36, .42 / max(Sw, 1e-3)), 4); w_, h_ = Sw * sc_, sc_   # khung rộng ~42 % (video ngang) / cao 36 % (video dọc)
        X = round(side * (.95 - w_ / 2 - .5) * 2, 4); Y = round(-((1 - .15 - h_ / 2) - .5) * 2, 4)   # góc dưới, chừa vùng nút TikTok
        pips.append(dict(media=sp['media'], src=round(sp['src_in'] + b['t0'] - sp['t0'] + .1, 3), t0=round(b['t0'] + .1, 3), t1=round(b['t1'] - .05, 3),
                         keys=[[round(b['t0'] + .1, 3), sc_, X, Y, -2.0 * side], [round(b['t1'] - .05, 3), sc_ * 1.06, X, Y + .02, 0.0]]))
    for a_, b_ in zip(ashots, ashots[1:]):   # khít liền, không hở
        if abs(a_['t1'] - b_['t0']) < .02: a_['t1'] = b_['t0']; a_['keys'][-1][0] = b_['t0']
    # SFX sinh động: whoosh khi cảnh phụ vào (cách nhau ≥ 2 s), "tách" nhẹ khi đổi cảnh phụ liền nhau
    wt = [x['t'] for x in sfx if 'whoosh' in x['file']]
    for k_, b in enumerate(bshots):
        prev = bshots[k_ - 1] if k_ else None
        if prev is not None and abs(prev['t1'] - b['t0']) < .01: continue
        if all(abs(b['t0'] - w) >= 2.0 for w in wt): sfx.append(dict(file='SFX whoosh mem.wav', t=max(0, round(b['t0'] - .22, 3)), vol=.22, dur=0.58)); wt.append(b['t0'])
    for x in sfx:
        if '/' not in x['file']: x['file'] = KSUB['sfx'] + '/' + x['file']
    for x in mus:
        if '/' not in x['file']: x['file'] = KSUB['music'] + '/' + x['file']
    return dict(project=proj, font_dir=adir + '/' + KSUB['font'], out_dir=os.path.join(L.TMP, 'out'), asset_dir=adir, media=media, total=total, lines=[dict(id='A', t0=0.0, t1=total)],
                apieces=[[p[4], round(p[3], 3), round(p[3] + p[2] - p[1], 3)] for p in pieces], ashots=ashots, bshots=bshots, pips=pips, speech=speech, shots=shots, titles=titles, transitions=trans, effects=fx, music=mus, sfx=sorted(sfx, key=lambda x: x['t']), matte=[])


# ---------------------------------------------------------------- nhạc nền: mỗi project 1 bài KHÁC NHAU (ưu tiên nhạc chủ để trong thư mục buổi quay, rồi tới Kho nhạc nền)
def used_music(add=None):
    cd = cache_dir(); f = lq("'%s' in parents and name='Nhạc đã dùng.txt'" % cd, 'id')
    ids = [x for x in raw(f[0]['id']).decode('utf-8').splitlines() if x.strip()] if f else []   # lưu TÊN bài (bài trùng tên ở chỗ khác cũng coi là đã dùng)
    if add and add not in ids:
        ids.append(add); data = '\n'.join(ids).encode('utf-8')
        if f: update(f[0]['id'], data, 'text/plain')
        else: put('Nhạc đã dùng.txt', cd, data, 'text/plain')
    return ids
def pick_music(jb, sc=None):
    try:
        AU = lambda d: [c for c in lq("'%s' in parents and mimeType contains 'audio/'" % d, 'id,name,size,mimeType') if int(c.get('size') or 0) > 800000
                        and not re.search(r'(?i)voice|vocal|giọng|giong|sfx|whoosh|lồng tiếng', c['name'])]
        local = [c for d in list(jb['dirs']) + [p[0] for p in jb.get('pool', [])] for c in AU(d)]
        kho = lq("'%s' in parents and name='Kho nhạc nền' and mimeType='%s'" % (cache_dir(), L.FOLDER), 'id')
        cands = local + (AU(kho[0]['id']) if kho else [])
        used = set(used_music()); fresh = [c for c in cands if nf(c['name']).lower() not in used] or cands
        if not fresh: return None
        c = fresh[0]
        if sc:   # Claude chọn nhạc hợp phong thái người nói + giọng kịch bản (không mặc định nhạc da diết)
            try:
                talk = [a for a in jb['A'] if not a['vid'].get('broll')][:4]
                info = 'Tên video: %s\nChữ nhấn: %s\nNgười nói / cảnh: %s' % (sc.get('ten', ''), ', '.join(t.get('big', '') for t in (sc.get('titles') or [])[:14]),
                                                                       ' | '.join(((a.get('vlog') or {}).get('tong') or '')[:160] for a in talk))
                opts = '\n'.join('%d. %s' % (k, x['name']) for k, x in enumerate(fresh[:40]))
                j = N.ask_json(info + '\n\nCHỌN 1 BÀI NHẠC NỀN hợp nhất với phong thái người nói và giọng điệu kịch bản (vd tự tin – năng động – hài hước → nhạc sôi, beat mạnh, hiện đại / trap / pop; chia sẻ cảm xúc thật sự mới dùng nhạc sâu lắng). '
                               'Video BĐS / kinh doanh mặc định: hiện đại, sang, có nhịp. Tránh nhạc da diết, bi, chậm buồn khi kịch bản không buồn.\nDanh sách (đoán tính chất qua tên):\n' + opts +
                               '\n\nTrả JSON {"chon": số thứ tự, "ly_do": "ngắn"}', model='sonnet', key='chon', log=log)
                if j is not None and 0 <= int(j['chon']) < len(fresh[:40]): c = fresh[int(j['chon'])]; log('  Claude chọn nhạc:', c['name'], '–', str(j.get('ly_do', ''))[:80])
            except ClaudeWait: raise
            except Exception as e: log('  Claude chưa chọn được nhạc, lấy bài mới nhất:', e)
        fp = os.path.join(L.TMP, 'nhac_' + c['id'])
        open(fp, 'wb').write(raw(c['id']))
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', fp], capture_output=True, text=True).stdout.strip() or 0)
        if dur < 20: return None
        ext = os.path.splitext(c['name'])[1].lower() or '.mp3'
        nm = 'Nhac nen - ' + re.sub(r'[^A-Za-z0-9 -]+', '', unicodedata.normalize('NFKD', os.path.splitext(c['name'])[0]).encode('ascii', 'ignore').decode())[:40].strip() + ext
        try: mm = X.music_map(fp)   # BPM, kick, snare, đoạn lắng / sôi, điểm dồn → cắt cảnh theo nhịp
        except Exception as e: mm = {}; log('  không phân tích được nhịp nhạc:', e)
        log('  nhạc nền:', c['name'], '(%.0fs, %s BPM, %d kick, %d snare)' % (dur, mm.get('bpm', '?'), len(mm.get('kicks') or []), len(mm.get('snares') or [])))
        return (c['id'], nm, round(dur, 3), nf(c['name']).lower(), mm)
    except Exception as e: log('  không chọn được nhạc riêng:', e); return None

KHO_NAME = 'Kho AI tải về'; KSUB = {'font': 'Font chữ', 'sfx': 'Âm thanh hiệu ứng', 'music': 'Nhạc nền', 'broll': 'Cảnh phụ tải về'}   # bản đồ 3D: nằm trong thư mục project CapCut của từng video (chủ dặn)   # cảnh phụ tải về đặt tên: "Dự án - nội dung"
_KHO = {}
def kho():   # KHO DÙNG CHUNG (chủ dặn 11/11): SETUP/Kho AI tải về/{Font chữ, Âm thanh hiệu ứng, Nhạc nền, Bản đồ 3D} – mọi project lấy từ đây
    if _KHO: return _KHO
    st = lq("'%s' in parents and name='SETUP' and mimeType='%s'" % (L.ROOT, L.FOLDER), 'id')[0]['id']
    def one(parent, nm):   # đúng 1 thư mục tên nm (nhiều máy tạo cùng lúc → gộp bản trùng vào bản cũ nhất, bỏ bản thừa)
        f = sorted(lq("'%s' in parents and name='%s' and mimeType='%s'" % (parent, nm, L.FOLDER), 'id,createdTime'), key=lambda x: x.get('createdTime') or '')
        if not f: mkdir(nm, parent); time.sleep(3); return one(parent, nm)
        keep = f[0]['id']
        for d in f[1:]:
            try:
                have = {x['name'] for x in lq("'%s' in parents" % keep, 'id,name')}
                for c in lq("'%s' in parents" % d['id'], 'id,name,mimeType'):
                    if c['name'] not in have: L.drive('files/%s' % c['id'], {}, method='PATCH', params={'addParents': keep, 'removeParents': d['id'], 'fields': 'id'})
                L.drive('files/' + d['id'], {'trashed': True}, method='PATCH'); log('  gộp thư mục trùng:', nm)
            except Exception as e: log('  không gộp được thư mục trùng', nm, e)
        return keep
    kid = one(st, KHO_NAME)
    _KHO.update(id=kid, rel='SETUP/' + KHO_NAME)
    for key, nm in KSUB.items(): _KHO[key] = one(kid, nm)
    for d in lq("'%s' in parents and name='Bản đồ 3D' and mimeType='%s'" % (kid, L.FOLDER), 'id'):   # bỏ thư mục cũ (nếu trống)
        try:
            if not lq("'%s' in parents" % d['id'], 'id'): L.drive('files/' + d['id'], {'trashed': True}, method='PATCH')
        except Exception: pass
    have = {key: {x['name'] for x in lq("'%s' in parents" % _KHO[key], 'id,name')} for key in ('font', 'sfx', 'music')}
    for f in lq("'%s' in parents and trashed=false" % LIB, 'id,name,mimeType'):   # chép 1 lần từ thư viện mẫu cũ
        if f.get('mimeType') == L.FOLDER or f['name'].startswith(LIB_SKIP): continue
        key = 'font' if f['name'].lower().endswith(('.ttf', '.otf')) else ('sfx' if re.match(r'(?i)sfx', f['name']) else ('music' if 'audio' in (f.get('mimeType') or '') or f['name'].lower().endswith(('.mp3', '.wav', '.m4a')) else None))
        if not key or f['name'] in have[key]: continue
        try: L.drive('files/%s/copy' % f['id'], {'name': f['name'], 'parents': [_KHO[key]]}, params={'fields': 'id'})
        except Exception:
            try: put(f['name'], _KHO[key], raw(f['id']), f.get('mimeType') or 'application/octet-stream')
            except Exception as e: log('  kho: bỏ file', f['name'], e)
    return _KHO
def kho_music(p_):   # bài nhạc được chọn → có trong Kho/Nhạc nền (giữ tên gốc dễ hiểu)
    k = kho(); nm = p_['orig']
    if not lq("'%s' in parents and name='%s'" % (k['music'], nm.replace("'", "\\'")), 'id'):
        try: L.drive('files/%s/copy' % p_['id'], {'name': nm, 'parents': [k['music']]}, params={'fields': 'id'})
        except Exception: put(nm, k['music'], raw(p_['id'], anon=True), 'audio/mpeg')

def music_info(c):   # phân tích 1 bài nhạc 1 lần (BPM, kick, snare, đoạn lắng / sôi, điểm dồn) – lưu lại cho mọi máy dùng
    ad, _ = ana_dir(); nm = '%s_nhac.json' % c['id']; got = names_in(ad, [nm])
    if nm in got:
        try: return json.loads(raw(got[nm]).decode('utf-8'))
        except Exception: pass
    fp = os.path.join(L.TMP, 'nhac_' + c['id']); open(fp, 'wb').write(raw(c['id'], anon=True))
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', fp], capture_output=True, text=True).stdout.strip() or 0)
    try: mm = X.music_map(fp)
    except Exception: mm = {}
    info = dict(dur=round(dur, 3), mm=mm)
    try: jput(nm, info, ad, {})
    except Exception: pass
    return info

def mnm(c): return KSUB['music'] + '/' + nf(c['name']).replace('/', ' ')   # đường dẫn trong kho: Nhạc nền/<tên gốc>

def pick_mix(jb, sc):   # Claude MIX nhạc theo từng đoạn kịch bản (1–3 bài, chuyển mượt) – ngầu, hiện đại, kịch tính; vui thì bẻ sang dòng nhạc có gu
    try:
        AU = lambda d: [c for c in lq("'%s' in parents and mimeType contains 'audio/'" % d, 'id,name,size,mimeType') if int(c.get('size') or 0) > 800000
                        and not re.search(r'(?i)voice|vocal|giọng|giong|sfx|whoosh|lồng tiếng', c['name'])]
        local = [c for d in list(jb['dirs']) + [p[0] for p in jb.get('pool', [])] for c in AU(d)]
        kho = lq("'%s' in parents and name='Kho nhạc nền' and mimeType='%s'" % (cache_dir(), L.FOLDER), 'id')
        cands = (local + AU(globals()['kho']()['music']) + (AU(kho[0]['id']) if kho else []))   # nhạc trong source + Kho chung (SETUP/Kho AI tải về/Nhạc nền) + kho nhạc cũ
        seen_ = set(); cands = [c for c in cands if not (nf(c['name']).lower() in seen_ or seen_.add(nf(c['name']).lower()))][:40]
        if not cands: return None
        used = set(used_music()); INF = {}
        for c in cands:
            try: INF[c['id']] = music_info(c)
            except Exception: pass
        cands = [c for c in cands if (INF.get(c['id']) or {}).get('dur', 0) >= 20]
        if not cands: return None
        C = jb.get('C') or codes(jb); A = {a['i']: a for a in jb['A']}; t, lines = 0.0, []
        for x in sc.get('aroll') or []:
            cc = C.get(str(x).strip().upper()) if isinstance(x, str) else None
            if not cc: continue
            a = A.get(cc[0]); txt = ' '.join(w[2] for w in words(a, cc[1], cc[2])) if a else ''
            lines.append('%.0fs: %s' % (t, txt[:120])); t += cc[2] - cc[1]
        est = max(t, 1.0)
        def feat(c):
            i = INF[c['id']]; mm = i.get('mm') or {}; sec = ', '.join('%d–%ds %s' % (a_, b_, l_) for a_, b_, l_ in (mm.get('sections') or [])[:8])
            return '%s | %.0fs | %s BPM | đoạn: %s | dồn: %s%s' % (c['name'], i['dur'], mm.get('bpm', '?'), sec, mm.get('drops') or [], ' | (đã dùng)' if nf(c['name']).lower() in used else '')
        opts = '\n'.join('%d. %s' % (k, feat(c)) for k, c in enumerate(cands))
        q = ('Video: %s – dài khoảng %.0f giây. Lời thoại theo giây:\n%s\n\n' % (sc.get('ten', ''), est, '\n'.join(lines)[:5000]) +
             'MIX NHẠC NỀN cho video này (chủ dặn): nhạc LUÔN ngầu, hiện đại, kịch tính, có gu – KHÔNG nhạc quảng cáo thông thường, KHÔNG vui tươi kiểu trẻ con, KHÔNG da diết.\n'
             '- Đoạn thể hiện quy mô / sức mạnh / con số lớn → trap, drill, bass house, rock, blues nặng, cinematic hybrid.\n'
             '- Đoạn nhẹ / vui / phong cách sống → bẻ lái mượt sang dòng nhạc có gu: jazz, valse, bossa nova, bedroom pop, dream pop, lo-fi sang.\n'
             '- Dùng 1–3 bài, mỗi bài phủ 1 đoạn liền (đổi bài ở chỗ đổi ý của kịch bản); ưu tiên bài chưa dùng; vào bài ở đoạn "sôi" / điểm dồn khi cần ngầu.\n'
             'Danh sách bài (tên | độ dài | BPM | đoạn lắng/vừa/sôi | điểm dồn):\n' + opts +
             '\n\nTrả JSON {"mix":[{"bai": số thứ tự, "tu": % thời lượng video bắt đầu (0–100), "den": % kết thúc, "vao": giây bắt đầu trong bài}], "ly_do": "ngắn"} – các đoạn nối liền, phủ 0→100.')
        j = N.ask_json(q, model='sonnet', key='mix', log=log)
        parts = []
        for m in (j or {}).get('mix') or []:
            try:
                c = cands[int(m['bai'])]; i = INF[c['id']]
                parts.append(dict(id=c['id'], nm=mnm(c), orig=nf(c['name']).replace('/', ' '), dur=i['dur'], key=nf(c['name']).lower(), mm=i.get('mm') or {}, f0=max(0, min(1, float(m['tu']) / 100)), f1=max(0, min(1, float(m['den']) / 100)), src=max(0.0, min(i['dur'] - 10, float(m.get('vao') or 0)))))
            except Exception: continue
        parts = sorted([p_ for p_ in parts if p_['f1'] - p_['f0'] > .05], key=lambda p_: p_['f0'])
        if not parts:
            fresh = [c for c in cands if nf(c['name']).lower() not in used] or cands; c = fresh[0]; i = INF[c['id']]
            parts = [dict(id=c['id'], nm=mnm(c), orig=nf(c['name']).replace('/', ' '), dur=i['dur'], key=nf(c['name']).lower(), mm=i.get('mm') or {}, f0=0.0, f1=1.0, src=0.0)]
        parts[0]['f0'] = 0.0; parts[-1]['f1'] = 1.0
        for a_, b_ in zip(parts, parts[1:]): b_['f0'] = a_['f1']
        log('  Claude mix nhạc:', ' → '.join('%s (%d–%d%%)' % (p_['nm'], p_['f0'] * 100, p_['f1'] * 100) for p_ in parts), '–', str((j or {}).get('ly_do', ''))[:100])
        return parts
    except ClaudeWait: raise
    except Exception as e: log('  không mix được nhạc:', e); return None

def engine():
    if os.path.exists(os.path.join(ENG, 'build.py')): return
    z = lq("'%s' in parents and name='%s' and trashed=false" % (cache_dir(), ENG_NAME))[0]['id']
    os.makedirs(ENG, exist_ok=True); p = os.path.join(L.TMP, 'eng.zip'); open(p, 'wb').write(raw(z)); zipfile.ZipFile(p).extractall(ENG)
    for fn in ('build.py',):   # mã bộ dựng mới nhất nằm trong kho GitHub (font, mẫu vẫn lấy từ Bộ dựng AI.zip)
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eng', fn)
        if os.path.exists(src): open(os.path.join(ENG, fn), 'wb').write(open(src, 'rb').read())
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'fonttools'], capture_output=True)

# ---------------------------------------------------------------- 4) đưa project lên Drive + danh sách lối tắt
def list_file():
    return lq("'%s' in parents and name='%s' and trashed=false" % (cache_dir(), LIST_NAME))[0]['id']
def list_edit(add=(), remove=()):   # danh sách lối tắt = TÍNH LẠI từ thông tin thư mục trên Drive (không cần đọc nội dung file → không bị chặn hạn mức tải, không ghi đè mất dòng)
    fid = list_file()
    lines = sorted({path_of((c.get('parents') or [''])[0]) + '/' + nf(c['name'])
                    for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s'" % L.FOLDER, 'id,name,parents')})
    update(fid, ('\r\n'.join(lines) + '\r\n').encode('utf-8'), 'text/plain')
def timeline(jb, sc, pl):   # dòng thời gian bằng chữ cho Claude kiểm duyệt
    A = {a['i']: a for a in jb['A']}; AK = {'V%d' % i: a for i, a in A.items()}; out = []
    for sh in pl['shots']:
        a = AK.get(sh['media']); src = sh['src']
        seg = []   # lời ĐANG PHÁT trên dòng thời gian (cả khi đang chiếu cảnh phụ – tiếng vẫn là A-roll)
        for sp in pl['speech']:
            lo, hi = max(sp['t0'], sh['t0']), min(sp['t1'], sh['t1'])
            if hi - lo > .05: seg += [w[2] for w in words(AK.get(sp['media']), sp['src_in'] + lo - sp['t0'], sp['src_in'] + hi - sp['t0'])]
        seg = ' '.join(seg)
        vl = next((d for d in ((a or {}).get('vlog') or {}).get('doan', []) if float(d.get('s', 0)) - .3 <= src <= float(d.get('e', 0)) + .3), None)
        tag = ('CẢNH PHỤ tự phủ lên bản thu tiếng (không bỏ được)' if sh.get('phu') else '[B%d] CẢNH PHỤ' % sh.get('bi', -1)) if sh['line'] != 'A' else 'NGƯỜI NÓI'
        out.append('%5.1f–%5.1fs %s (video #%d từ giây gốc %.1f) zoom %.2f→%.2f%s | hình: %s | lời đang phát: %s' % (sh['t0'], sh['t1'], tag, a['i'] if a else 0, src, sh['keys'][0][1], sh['keys'][-1][1],
                   ' (có giật zoom)' if len(sh['keys']) > 2 else '', (vl or {}).get('noi_dung', '?') + ' / ' + (vl or {}).get('chat_luong', ''), seg[:160]))
    for z in pl['titles']:
        out.append('%5.1f–%5.1fs [T%d] CHỮ y=%.0f%%: %s' % (z['t0'], z['t1'], z['si'], z['y_pct'], ' / '.join(l[0] for l in z['lines'])))
    out.sort(key=lambda r: float(r.split('–')[0]))
    out.append('Chuyển cảnh: ' + ', '.join('%s@%.1fs' % (x['name'], x['at']) for x in pl['transitions']) + ' · tổng %.1fs' % pl['total'])
    return ('DỰ ÁN (tên chuẩn theo thư mục): %s – lời thoại do máy nghe có thể sai tên riêng (vd "Kinh Bắc" = "King Park"); chữ trên hình sai tên dự án / địa danh là lỗi NẶNG, sửa bằng doi_chu.\n' % path_of(jb['id'])) + '\n'.join(out)
def review(jb, sc, pl, proj, adir, mu):
    sc0 = sc
    rows = []   # KHO CẢNH PHỤ cho Claude đổi cảnh phụ vớ vẩn: các đoạn đẹp nhất (Claude đã chấm khi xem)
    for a in jb['A']:
        if not (a['vid'].get('broll') or not a.get('segs')): continue
        for x in sorted(((a.get('vlog') or {}).get('doan') or []), key=lambda x: -float(x.get('diem') or 0))[:2]:
            if float(x.get('diem') or 0) >= 7 and float(x.get('e', 0)) - float(x.get('s', 0)) >= 2: rows.append((float(x.get('diem') or 0), '#%d %.1f–%.1fs: %s' % (a['i'], float(x['s']), float(x['e']), str(x.get('noi_dung', ''))[:70])))
    # CÂU KẾT / CÂU HÚT ỨNG VIÊN của CHÍNH nhân vật đang nói (cùng video A-roll), lấy từ toàn source – được dùng lại câu ở kịch bản khác
    C_ = jb.get('C') or codes(jb); A_ = {a['i']: a for a in jb['A']}
    used_v = {C_[str(x).strip().upper()][0] for x in sc.get('aroll') or [] if isinstance(x, str) and str(x).strip().upper() in C_}
    END = re.compile(r'(?i)comment|bình luận|liên hệ|inbox|nhắn tin|theo dõi|follow|đăng ký|để lại|cảm ơn|hẹn gặp|nghĩ sao|ý kiến|đừng bỏ lỡ|nhanh tay|còn chần chừ|gọi ngay|hotline|kết lại|tóm lại|vậy thì|chính vì vậy')
    endc = []
    for k_, (vi_, s_, e_) in C_.items():
        if vi_ not in used_v or not A_.get(vi_): continue
        tx = ' '.join(w[2] for w in words(A_[vi_], s_, e_))
        if END.search(tx) and 1.5 < e_ - s_ < 14: endc.append('%s (%.1fs): %s' % (k_, e_ - s_, tx[:110]))
    ecat = ('\n\nCÂU KẾT / CÂU HÚT CÓ THỂ GẮN THÊM (cùng nhân vật chính, mã câu C…):\n' + '\n'.join(endc[:40])) if endc else ''
    sty_ = (jget('%s_kichban.json' % jb['id'], idx_now()[1]) or {}).get('phong_cach') or style_of(jb)
    bcat = ('\n\nPHONG CÁCH KÊNH (video đã hậu kỳ trước đó – bản dựng phải theo, lệch phong cách là lỗi):\n' + sty_ if sty_ else '') + ecat + ('\n\nKHO CẢNH PHỤ (đoạn đẹp, đã chấm điểm):\n' + '\n'.join(r_[1] for r_ in sorted(rows, key=lambda r_: -r_[0])[:60])) if rows else ''
    A = {'V%d' % a['i']: a for a in jb['A']}
    for rnd in range(4):   # 1 lần kiểm + tối đa 3 lần sửa
        ts = sorted({round((z['t0'] + z['t1']) / 2, 2) for z in pl['titles']} | {round(x['t0'] + .3, 2) for x in pl['shots'] if x['line'] != 'A'})
        if len(ts) > 24: ts = ts[::math.ceil(len(ts) / 24)]
        try: pv = N.preview(pl, A, ts, os.path.join(ENG, 'fonts'))
        except Exception as e: pv = []; log('  không dựng được ảnh xem trước:', e)
        r = N.qa(pl, timeline(jb, sc, pl), pv, log=log, extra=bcat)
        if r is None: raise ClaudeWait('Claude chưa kiểm tra được bản dựng')
        log('  kiểm tra vòng %d: %s%s' % (rnd + 1, 'ĐẠT' if r.get('dat') else 'chưa đạt', '' if r.get('dat') else ' – ' + '; '.join(map(str, r.get('loi') or []))[:400]))
        if r.get('dat') and (rnd >= 1 or not (r.get('sua') and any((r.get('sua') or {}).values()))): return pl   # mọi project ít nhất 2 lượt Claude xem nếu còn chỗ sửa (chất lượng đồng đều)
        fx = r.get('sua') or {}; sc = json.loads(json.dumps(sc)); T = sc.get('titles') or []
        for d in fx.get('doi_chu') or []:
            try: T[int(d['T'])].update(big=d.get('big', T[int(d['T'])].get('big')), small=d.get('small', ''))
            except Exception: pass
        for d in fx.get('doi_vi_tri') or []:
            try: T[int(d['T'])]['y'] = float(d['y'])
            except Exception: pass
        drop = {int(x) for x in fx.get('bo_chu') or [] if str(x).lstrip('-').isdigit()}
        sc['titles'] = [t for i, t in enumerate(T) if i not in drop] + [t for t in fx.get('them_chu') or [] if isinstance(t, dict) and t.get('cau')]
        aro0 = list(sc.get('aroll') or [])
        for c in fx.get('cat_doan') or []:   # bỏ câu bị cắt hỏng / nói hỏng (theo giây trên timeline)
            try:
                s_, e_ = float(c['s']), float(c['e'])
                ai_ = {p[0] for p in pl.get('apieces') or [] if min(e_, p[2]) - max(s_, p[1]) > .15}
                if ai_ and len(ai_) < len(sc.get('aroll') or []): sc['aroll'] = [x for i, x in enumerate(sc['aroll']) if i not in ai_]
            except Exception: pass
        for c in fx.get('khung_rong') or []:
            try: sc.setdefault('_wide', []).append([float(c['s']), float(c['e'])])
            except Exception: pass
        for c in fx.get('doi_canh_tu_phu') or []:   # cảnh tự phủ xấu → không dùng đoạn đó nữa
            try: sc.setdefault('_bad', []).append([int(c['video']), float(c['giay'])])
            except Exception: pass
        for c in fx.get('doi_canh_phu') or []:   # đổi cảnh phụ vớ vẩn bằng đoạn đẹp trong kho (giữ đúng chỗ chèn)
            try:
                bi_ = int(c['B']); B_ = sc.get('broll') or []
                if 0 <= bi_ < len(B_): B_[bi_] = dict(B_[bi_], video=int(c['video']), s=float(c['s']), e=float(c['s']) + 3)
            except Exception: pass
        for c in fx.get('them_cau') or []:   # gắn câu kết (cuối) / câu hút (đầu) – dùng lại được câu ở kịch bản khác
            try:
                cc_ = str(c.get('cau', '')).strip().upper()
                if cc_ in C_ and cc_ not in [str(x).strip().upper() for x in sc.get('aroll') or []]:
                    sc['aroll'] = ([cc_] + list(sc['aroll'])) if c.get('vi_tri') == 'dau' else (list(sc['aroll']) + [cc_])
            except Exception: pass
        bdrop = {int(x) for x in fx.get('bo_canh_phu') or [] if str(x).lstrip('-').isdigit()}
        sc['broll'] = [b for i, b in enumerate(sc.get('broll') or []) if i not in bdrop]
        if rnd == 3: break   # vòng cuối: vẫn ghi lại các chỗ sửa để lượt sau dựng tiếp từ đó
        pl2 = build_plan(jb, sc, proj, adir, mu, None)
        if not pl2 and fx.get('cat_doan') and aro0 is not None:   # bỏ câu làm video quá ngắn → giữ lại câu đó
            sc['aroll'] = aro0; pl2 = build_plan(jb, sc, proj, adir, mu, None)
        if not pl2: break
        pl = pl2
    log('  ✗ Claude kiểm tra chưa đạt sau 3 vòng sửa – KHÔNG giao project này:', proj); jb['qa_rej'] = jb.get('qa_rej', 0) + 1; jb['fixed'] = dict(sc, _n=sc0.get('_n')); return None
GKEYS = ('brightness', 'contrast', 'saturation', 'temperature', 'tone', 'highlight', 'shadow')
def claude_grades(jb, sc):   # Claude Sonnet NHÌN khung hình từng video dùng trong kịch bản → thông số lớp màu riêng (lưu lại, mỗi video xem 1 lần)
    try:
        from PIL import Image, ImageDraw
        A = {a['i']: a for a in jb['A']}; C = jb.get('C') or {}; use = set()
        for x in sc.get('aroll') or []:
            c = C.get(str(x).strip().upper()) if isinstance(x, str) else None
            if c: use.add(c[0])
        for b in sc.get('broll') or []:
            try: use.add(int(re.sub(r'\D', '', str(b.get('video', 0))) or 0))
            except Exception: pass
        ad, _ = ana_dir(); need = []
        for i in sorted(use):
            a = A.get(i)
            if not a: continue
            nm = '%s_%s_mau.json' % (a['vid']['id'], a['vid'].get('size') or 0)
            got = names_in(ad, [nm])
            if nm in got:
                try: a['mau'] = json.loads(raw(got[nm]).decode('utf-8')); continue
                except Exception: pass
            need.append((a, nm))
        for g in range(0, len(need), 12):
            grp = need[g:g + 12]; tiles = []
            for a, nm in grp:
                ts = [t for s_ in (a.get('see') or {}).get('sheets') or [] for t in s_['ts']]
                im = N._tile(a, ts[len(ts) // 2]) if ts else None
                if im is not None: tiles.append((a, nm, im))
            if not tiles: continue
            w, h = max(t[2].width for t in tiles), max(t[2].height for t in tiles); cols = 4
            cv = Image.new('RGB', (cols * w, ((len(tiles) + cols - 1) // cols) * h), (0, 0, 0)); dr = ImageDraw.Draw(cv)
            for k, (a, nm, im) in enumerate(tiles):
                x, y = (k % cols) * w, (k // cols) * h; cv.paste(im, (x, y)); dr.rectangle([x, y, x + 40, y + 16], fill=(0, 0, 0)); dr.text((x + 3, y + 2), '#%d' % a['i'], fill=(255, 230, 80))
            bio = io.BytesIO(); cv.save(bio, 'JPEG', quality=80)
            meas = '\n'.join('#%d: đo được %s' % (a['i'], json.dumps(grade_of(dict(a, mau=None)), ensure_ascii=False)) for a, nm, im in tiles)
            q = ('Ảnh = 1 khung hình gốc (chưa chỉnh) của từng video, góc trái ghi số #. Hãy đặt thông số lớp Điều chỉnh màu CapCut cho TỪNG video để cả project ra cùng 1 tông:\n'
                 'MÀU MẪU CỦA CHỦ: điện ảnh, chuyên nghiệp, hiện đại, sang, sạch; RÕ (tương phản tốt, chi tiết sắc), BÃO HÒA rõ (cỏ cây xanh tươi, trời xanh, da hồng hào) nhưng vẫn TƯƠI SÁNG, trắng sạch không ám, vùng tối không bệt, vùng sáng không cháy.\n'
                 'Cảnh đã đẹp sẵn thì chỉnh nhẹ; cảnh xỉn / mù / log / thiếu sáng thì chỉnh mạnh hơn. Gợi ý máy đo (tham khảo):\n' + meas +
                 '\n\nThang giá trị (0 = giữ nguyên): brightness −0.3..0.35, contrast −0.2..0.5, saturation −0.3..0.5, temperature −0.35..0.35 (dương = ấm), tone −0.25..0.25 (dương = hồng, âm = xanh lá), highlight −0.4..0, shadow −0.1..0.3.\n'
                 'Trả JSON {"videos":[{"video":số #,"brightness":..,"contrast":..,"saturation":..,"temperature":..,"tone":..,"highlight":..,"shadow":..}]}')
            j = N.ask_json(q, [('Khung hình gốc:', base64.b64encode(bio.getvalue()).decode())], model='sonnet', key='videos', log=log)
            if not j: continue
            R = {'brightness': (-.3, .35), 'contrast': (-.2, .5), 'saturation': (-.3, .5), 'temperature': (-.35, .35), 'tone': (-.25, .25), 'highlight': (-.4, 0), 'shadow': (-.1, .3)}
            by = {a['i']: (a, nm) for a, nm, im in tiles}
            for v in j.get('videos') or []:
                try: a, nm = by[int(v['video'])]
                except Exception: continue
                g = {k: round(max(R[k][0], min(R[k][1], float(v.get(k) or 0))), 3) for k in GKEYS}
                a['mau'] = g
                try: jput(nm, g, ad, {})
                except Exception: pass
            log('  Claude xem màu %d video, đặt thông số lớp màu' % len(tiles))
    except ClaudeWait: raise
    except Exception as e: log('  Claude chưa đặt được màu (dùng thông số máy đo):', e)

XM = '❌ '   # project cũ đang được AI dựng lại (sẽ bị thay khi bản mới lên xong)
def user_edited(c):   # người dùng đã mở CapCut và lưu chỉnh sửa → project là của họ, AI không thay / không xóa
    try:
        f = lq("'%s' in parents and name='draft_content.json'" % c['id'], 'id')
        ut = float(json.loads(raw(f[0]['id']).decode('utf-8')).get('update_time') or 0) if f else 0
        ut = ut / 1e6 if ut > 1e11 else ut
        return ut > L.ts(c['createdTime']) + 300
    except Exception: return True   # không chắc → coi như đã sửa, giữ lại cho an toàn
def ren(c, par, new):   # đổi tên thư mục project + đường dẫn bên trong + danh sách CapCut
    old = nf(c['name']); oldrel, newrel = path_of(par) + '/' + old, path_of(par) + '/' + new
    for f in lq("'%s' in parents and (name='draft_content.json' or name='draft_info.json' or name='draft_meta_info.json')" % c['id'], 'id,name'):
        try:
            t = unicodedata.normalize('NFC', raw(f['id']).decode('utf-8'))
            t2 = t.replace('/' + old + '/', '/' + new + '/').replace('\\' + old + '\\', '\\' + new + '\\').replace('"' + old + '"', '"' + new + '"')
            if t2 != t: update(f['id'], t2.encode('utf-8'), 'application/json')
        except Exception as e: log('  đổi tên: không sửa được', f['name'], e)
    L.drive('files/' + c['id'], {'name': new}, method='PATCH')
    list_edit(add=[newrel], remove=[oldrel]); c['name'] = new
def mark_old(host, slot, on=True):   # gắn / bỏ ❌ ở project cũ (chưa bị người dùng sửa) của đúng kịch bản này
    for c in lq("'%s' in parents and appProperties has { key='dungP' and value='1' } and trashed=false" % host, 'id,name,appProperties,createdTime'):
        ap = c.get('appProperties') or {}
        if ap.get('dungS') != slot or ap.get('dungL') == LV: continue
        nm = nf(c['name'])
        try:
            if on and not nm.startswith(XM) and not user_edited(c): ren(c, host, XM + nm); log('  đánh dấu ❌ project cũ đang được dựng lại:', nm)
            elif not on and nm.startswith(XM): ren(c, host, nm[len(XM):]); log('  bỏ ❌ (dựng lại chưa xong):', nm)
        except Exception as e: log('  không đổi được dấu ❌', nm, e)

def publish(jb, sc, n):
    a0 = jb['A'][0]; A_ = {a['i']: a for a in jb['A']}; cnt = {}
    for it in sc.get('aroll', []):   # project nằm trong thư mục (Kịch bản N) chứa phần lớn câu nói của kịch bản
        c = (jb.get('C') or {}).get(str(it).strip().upper()) if isinstance(it, str) else None
        a = A_.get(c[0]) if c else A_.get(int(re.sub(r'\D', '', str(it.get('video', 0))) or 0)) if isinstance(it, dict) else None
        if a: d = (jb.get('kbtop') or {}).get(a['vid']['dir'], a['vid']['dir']); cnt[d] = cnt.get(d, 0) + 1
    host = max(cnt, key=cnt.get) if cnt else jb['id']
    proj = safe(full_name(path_of(host), safe(re.sub(r'(?i)^(capcut|kịch bản|kich ban|kb)\s*\d*\s*[-–:]*\s*', '', sc.get('ten') or '') or '%s %d' % (jb['name'], n), 60)), 110)   # 🤖 dự án - nội dung
    rel = path_of(host) + '/' + proj; adir = DRV + '/' + kho()['rel']   # tài nguyên dựng lấy từ kho chung SETUP/Kho AI tải về
    slot0 = '%s:%d' % (jb['id'], n); mark_old(host, slot0, True)
    try: r_ = _publish(jb, sc, n, host, proj, rel, adir)
    except Exception: mark_old(host, slot0, False); raise
    if not r_ or r_.get('exists'): mark_old(host, slot0, False)
    return r_

def _publish(jb, sc, n, host, proj, rel, adir):
    a0 = jb['A'][0]
    mu = pick_mix(jb, sc); claude_grades(jb, sc)
    pl = build_plan(jb, sc, proj, adir, mu, None)
    if not pl: log('  bỏ kịch bản quá ngắn:', proj); return None
    pl = review(jb, sc, pl, proj, adir, mu)   # Claude Opus tự kiểm tra (xem ảnh xem trước + dòng thời gian), sửa tối đa 2 vòng
    if not pl: return None
    bad = []   # tự kiểm tra trước khi đẩy lên Drive – đã đẩy là không rút lại
    if not 40 <= pl['total'] <= 120: bad.append('dài %.0fs (cần 40–120s)' % pl['total'])
    if len(pl.get('titles') or []) < pl['total'] / 8.0: bad.append('chỉ %d chữ nhấn / %.0fs (cần ~1 cụm mỗi 1–3 s)' % (len(pl.get('titles') or []), pl['total']))
    if any(m.get('kind') == 'video' and not m.get('path') for m in pl['media'].values()): bad.append('thiếu file')
    if len([x for x in pl['shots'] if x.get('line') != 'A']) < 2: bad.append('quá ít cảnh phụ')
    if bad: log('  chưa đạt, không đẩy lên:', proj, '–', ', '.join(bad)); return None
    pp = os.path.join(L.TMP, 'plan_%d.json' % n); json.dump(pl, open(pp, 'w'), ensure_ascii=False)
    r = subprocess.run([sys.executable, os.path.join(ENG, 'build.py'), pp], capture_output=True, text=True, timeout=600)
    od = os.path.join(pl['out_dir'], proj)
    if not os.path.exists(os.path.join(od, 'draft_content.json')): raise RuntimeError('dựng lỗi: ' + (r.stderr or r.stdout)[-300:])
    inhost = [c for c in lq("'%s' in parents and appProperties has { key='dungP' and value='1' } and trashed=false" % host, 'id,name,appProperties,createdTime')]
    new_ = [c for c in inhost if (c.get('appProperties') or {}).get('dungL') == LV]
    old_ = [c for c in inhost if (c.get('appProperties') or {}).get('dungL') != LV]   # bản dựng kiểu cũ (1 track) → chủ dặn dựng lại rồi thay
    if host in set((jb.get('kbtop') or {}).values()) and new_:
        log('  thư mục này đã có project – giữ nguyên:', path_of(host)); return dict(proj=proj, dur=0, exists=True)   # mỗi thư mục Kịch bản 1 project
    slot = '%s:%d' % (jb['id'], n)
    if any((c.get('appProperties') or {}).get('dungS') == slot or c['name'] == proj for c in new_):
        log('  đã có project này trên Drive – giữ nguyên, không ghi đè:', proj); return dict(proj=proj, dur=0, exists=True)
    bare = lambda nm: nf(nm)[len(XM):] if nf(nm).startswith(XM) else nf(nm)
    old_ = [c for c in old_ if (c.get('appProperties') or {}).get('dungS') == slot or bare(c['name']) == proj]   # chỉ bản cũ của ĐÚNG kịch bản này (không đụng project khác cùng thư mục)
    keep_ = [c for c in old_ if user_edited(c)]
    old_ = [c for c in old_ if c not in keep_]
    if any(c['name'] == proj for c in keep_):   # bản người dùng đã sửa trùng tên → bản AI mới đặt tên khác, đứng cạnh
        proj = safe(proj + ' (AI dựng lại)', 120); rel = path_of(host) + '/' + proj
    for c in keep_: log('  giữ nguyên project người dùng đã chỉnh sửa:', c['name'])
    pf = mkdir(proj, host, {'dungP': '1', 'dungS': slot, 'dungL': LV, 'dungVol': '1'})   # đánh dấu thư mục project (tên không còn chữ CapCut)
    try:
        for p_ in {p_['id']: p_ for p_ in (mu or [])}.values(): kho_music(p_)   # nhạc dùng → vào Kho/Nhạc nền
        for fn in ('draft_content.json', 'draft_info.json', 'draft_meta_info.json'):
            put(fn, pf, open(os.path.join(od, fn), 'rb').read(), 'application/json')   # giữ G:/Drive của tôi/…; công cụ đồng bộ trên từng máy tự sửa theo ổ Drive thật của máy đó (không bắt buộc ổ M)
        list_edit(add=[rel])
        for p_ in (mu or []): used_music(add=p_['key'])
        for c in old_:   # bản mới đã lên xong → mới bỏ bản cũ (vào thùng rác Drive, khôi phục được)
            try:
                L.drive('files/' + c['id'], {'trashed': True}, method='PATCH')
                if c['name'] != proj: list_edit(remove=[path_of(host) + '/' + c['name']])   # cùng tên → dòng danh sách giờ trỏ bản mới, giữ nguyên
                log('  đã thay bản cũ:', c['name'])
            except Exception as e: log('  không bỏ được bản cũ', c['name'], e)
    except Exception:   # hỏng giữa chừng → bỏ thư mục dở, không để rác
        try: L.drive('files/' + pf, {'trashed': True}, method='PATCH')
        except Exception: pass
        raise
    vid0 = next((A_[int(sh['media'][1:])]['vid']['id'] for sh in pl['shots'] if sh.get('line') == 'A' and sh['media'][1:].isdigit() and int(sh['media'][1:]) in A_), None) if (A_ := {a['i']: a for a in jb['A']}) else None
    return dict(proj=proj, dur=pl['total'], id=pf, url='https://drive.google.com/drive/folders/' + pf, thumb=vid0)

# ---- nhiều máy GitHub chạy song song: mỗi máy giữ 1 thư mục source (khóa trên Drive), máy khác bỏ qua
WID = '%s-%s' % (os.environ.get('GITHUB_RUN_ID', 'local'), os.environ.get('WORKER', '1'))
LOCK_TTL = 50 * 60
def _lock_of(fid):
    try: return (L.drive('files/' + fid, params={'fields': 'appProperties'}).get('appProperties') or {}).get('dungLock') or ''
    except Exception: return ''
def claim(jb):
    lk = _lock_of(jb['id'])
    if lk and not lk.startswith(WID + ':'):
        try:
            if time.time() - float(lk.rsplit(':', 1)[1]) < LOCK_TTL: return False
        except Exception: pass
    L.mark(jb['id'], dungLock='%s:%d' % (WID, time.time())); time.sleep(5)
    return _lock_of(jb['id']).startswith(WID + ':')   # 2 máy giành cùng lúc → chỉ 1 máy giữ được
def keep(jb):
    try: L.mark(jb['id'], dungLock='%s:%d' % (WID, time.time()))
    except Exception: pass
def release(jb):
    try:
        if _lock_of(jb['id']).startswith(WID + ':'): L.mark(jb['id'], dungLock=None)
    except Exception: pass

_NC = [0, False]
CODE = ('dung.py', 'nao.py', 'xem.py', 'loc.py', 'eng/', 'capcut/')   # công cụ đồng bộ mới → lượt máy mới đưa lên SETUP ngay
def newer_code():   # có bản sửa mới trên GitHub (mã dựng) → làm nốt kịch bản đang dở rồi dừng, lượt sau chạy ngay bằng mã mới
    if _NC[1] or time.time() - _NC[0] < 90: return _NC[1]
    _NC[0] = time.time(); d = os.path.dirname(os.path.abspath(__file__))
    try:
        if subprocess.run(['git', '-C', d, 'fetch', '-q', '--depth=1', 'origin', 'main'], capture_output=True, timeout=60).returncode: return False
        ch = subprocess.run(['git', '-C', d, 'diff', '--name-only', 'HEAD', 'FETCH_HEAD'], capture_output=True, text=True, timeout=30).stdout.split()
        _NC[1] = any(f.startswith(CODE) for f in ch)
        if _NC[1]: log('  có mã dựng mới trên GitHub → làm nốt việc đang dở rồi dừng để lượt sau dùng mã mới')
    except Exception: pass
    return _NC[1]

def edit(jb, key, models):
    # chủ dặn: ĐỌC source 1 lần → LÊN KỊCH BẢN 1 lần (lưu lại, không lên lại) → chỉ lặp DỰNG → XEM → SỬA cho tới khi đạt
    t0 = time.time(); ad = jb.get('ad')
    kb_nm = '%s_kichban.json' % jb['id']; book = None
    if kb_nm in (jb.get('idx') or {}):
        try: book = json.loads(raw(jb['idx'][kb_nm]).decode('utf-8'))
        except Exception: book = None
    def save():
        if ad:
            try: put(kb_nm, ad, json.dumps(book, ensure_ascii=False).encode('utf-8'), 'application/json')
            except Exception as e: log('  không lưu được kịch bản:', e)
    engine()
    if book:
        codes(jb)
    else:
        olds = [c['name'] for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s' and trashed=false" % L.FOLDER, 'name,appProperties')
                if str((c.get('appProperties') or {}).get('dungS', '')).startswith(jb['id'] + ':') and (c.get('appProperties') or {}).get('dungL') != LV]
        hint = ('CHỦ YÊU CẦU DỰNG LẠI (giữ đúng chủ đề, làm tốt hơn) các video đã giao: %s. Đưa các chủ đề này vào danh sách kịch bản trước.\n\n' % '; '.join(olds)) if olds else ''
        scs = plan(jb, key, models, hint)
        for n, sc in enumerate(scs, 1): sc['_n'] = n
        book = {'scripts': scs, 'done': [], 'tries': {}}; save()
        log('  đã lưu %d kịch bản – từ giờ chỉ dựng / xem / sửa, không lên lại kịch bản' % len(scs))
    MAXT = 6
    todo = [sc for sc in book['scripts'] if sc['_n'] not in book['done'] and int(book['tries'].get(str(sc['_n']), 0)) < MAXT]
    log('  %d kịch bản cần dựng (đã xong %d / %d)' % (len(todo), len(book['done']), len(book['scripts'])))
    done = []
    for sc in todo:
        if newer_code(): break
        keep(jb)
        n = sc['_n']; jb['fixed'] = None; jb['qa_rej'] = 0
        try:
            r = publish(jb, sc, n)
            if r:
                book['done'].append(n); done.append(r); log('  ✓ %s (%.0fs) – %.1f phút' % (r['proj'], r['dur'], (time.time() - t0) / 60))
                if not r.get('exists'):
                    try: tot = len(lq("appProperties has { key='dungL' and value='%s' } and mimeType='%s' and trashed=false" % (LV, L.FOLDER), 'id'))
                    except Exception: tot = 0
                    L.tsay('✅ AI DỰNG XONG PROJECT – ĐÃ ĐẨY LỐI TẮT\n🎬 %s (%d giây)\n📁 %s\n📊 Tổng đã hoàn thành: %d project\n💻 Mở CapCut là thấy (lối tắt tự vào máy trong ~2 phút)' % (r['proj'], r['dur'], path_of(jb['id']), tot))
            else:
                book['tries'][str(n)] = int(book['tries'].get(str(n), 0)) + 1
                if not jb.get('qa_rej'): book['tries'][str(n)] = MAXT; log('  kịch bản %d không dựng được (thiếu câu / quá ngắn) – bỏ qua' % n)
                if jb.get('fixed'):   # giữ các chỗ Claude đã sửa (chữ, cảnh, câu) → lượt sau sửa tiếp từ đó, không làm lại từ đầu
                    book['scripts'] = [jb['fixed'] if x['_n'] == n else x for x in book['scripts']]
                log('  kịch bản %d chưa đạt (lần %d/%d) – lượt sau dựng / sửa tiếp' % (n, book['tries'][str(n)], MAXT))
        except ClaudeWait: save(); raise
        except Exception as e:
            book['tries'][str(n)] = int(book['tries'].get(str(n), 0)) + 1; log('  ✗ kịch bản', n, e)
        save()
    left = [sc for sc in book['scripts'] if sc['_n'] not in book['done'] and int(book['tries'].get(str(sc['_n']), 0)) < MAXT]
    if left:
        L.mark(jb['id'], dungFailV=DV, dungErr='còn %d kịch bản đang dựng / sửa' % len(left), dungFail=None)
        return done
    L.mark(jb['id'], dungV=DV, dungN=len(book['done']), dungT=int(time.time()), dungFail=None)
    if len(book['done']) < len(book['scripts']): log('  %d kịch bản sửa %d lần vẫn chưa đạt – bỏ qua, chờ người xem' % (len(book['scripts']) - len(book['done']), MAXT))
    return done

# ---------------------------------------------------------------- vòng chạy: đọc trước 1 buổi trong lúc dựng buổi hiện tại
ONLY = ''   # bỏ trống ('') = chạy mọi thư mục source
PAUSE = False   # chủ dặn: tạm dừng giao project cho tới khi bản nâng cấp lớn (Claude xem dày khung hình, âm thanh, nhịp nhạc, tracking, tự kiểm tra) xong
# ================================================================ HÀNG VIỆC CHUNG cho mọi máy GitHub (chủ dặn 11/11)
# mọi máy = 1 cỗ máy: việc chia nhỏ (ĐỌC 1 video · LÊN KỊCH BẢN 1 source · DỰNG 1 kịch bản); máy rảnh nhận việc gần xong nhất trước
# (dựng → lên kịch bản → đọc) → project ra lần lượt, các máy còn lại vẫn đọc song song các source khác. Khóa từng việc trên Drive.
MAXT = 6
def _fresh(t):
    try: return t and time.time() - float(str(t).rsplit(':', 1)[1]) < LOCK_TTL
    except Exception: return False
def lock(fid, k):
    try:
        cur = (get(fid, 'appProperties').get('appProperties') or {}).get(k) or ''
        if cur and not cur.startswith(WID + ':') and _fresh(cur): return False
        L.mark(fid, **{k: '%s:%d' % (WID, time.time())}); time.sleep(2.5)
        return ((get(fid, 'appProperties').get('appProperties') or {}).get(k) or '').startswith(WID + ':')
    except Exception as e: log('  khóa lỗi', e); return False
def unlock(fid, k):
    try: L.mark(fid, **{k: None})
    except Exception: pass
def idx_now():
    ad, _ = ana_dir(); _ANA[1] = {x['name']: x['id'] for x in lq("'%s' in parents" % ad, 'id,name')}; return ad, _ANA[1]
def jget(name, idx):
    if name not in idx: return None
    try: return json.loads(raw(idx[name]).decode('utf-8'))
    except Exception: return None
def jput(name, obj, ad, idx):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    if name in idx: update(idx[name], data, 'application/json')
    else: idx[name] = put(name, ad, data, 'application/json')['id']
def st_name(jb, n): return '%s_kb%d_L%s.json' % (jb['id'], n, LV)   # trạng thái từng kịch bản theo kiểu dựng (đổi kiểu → dựng lại, bản cũ được thay)

def tasks(jobs=None):
    ad, idx = idx_now(); out = []
    for jb in (jobs if jobs is not None else scan()):
        kb = '%s_kichban.json' % jb['id']
        if kb in idx:
            book = jget(kb, idx) or {}; locks = get(idx[kb], 'appProperties').get('appProperties') or {}
            left = 0
            for sc in book.get('scripts') or []:
                n = sc['_n']; stt = jget(st_name(jb, n), idx) or {}
                if stt.get('done') or int(stt.get('tries') or 0) >= MAXT: continue   # 'done' = sổ kiểu cũ
                left += 1
                if not _fresh(locks.get('L%d' % n)): out.append((0, 'build', jb, n))
            if not left: L.mark(jb['id'], dungV=DV, dungFail=None); log('  %s: đã dựng xong mọi kịch bản' % jb['name'])
            continue
        unread = [v for v in jb['vids'] if hong_name(v) not in idx and (ana_name(v) not in idx or xem_name(v) not in idx)]
        if unread:
            out += [(2, 'read', jb, v) for v in unread if not _fresh((v.get('appProperties') or {}).get('dungRL'))]
        elif not _fresh(jb['ap'].get('dungLock')): out.append((1, 'plan', jb, None))
    import random
    random.shuffle(out); out.sort(key=lambda x: (1 if 'center avenue' in L.norm1(path_of(x[2]['id'])) else 0, x[0], 0 if 'academy' in L.norm1(path_of(x[2]['id'])) else 1))   # dựng (kịch bản có sẵn, gồm dựng lại project cũ) trước; cùng loại việc thì MICC Academy trước   # gần xong làm trước; cùng mức thì xáo để các máy không giành nhau
    return out

_JB = {}
def load(jb):   # nạp đủ dữ liệu 1 source (đã đọc hết → chỉ tải bộ nhớ đệm, ~30 giây); giữ trong máy cho các kịch bản sau
    if jb['id'] not in _JB: _JB[jb['id']] = read(jb)
    return _JB[jb['id']]

def names_in(ad, names):   # hỏi đúng vài file cần (không liệt kê cả kho phân tích hàng nghìn file)
    q = ' or '.join("name='%s'" % n for n in names)
    return {x['name']: x['id'] for x in lq("'%s' in parents and (%s)" % (ad, q), 'id,name')}
def do_read(jb, v):
    ad, _ = ana_dir(); t0 = time.time()
    idx = names_in(ad, [ana_name(v), xem_name(v), hong_name(v)])
    if hong_name(v) in idx or (ana_name(v) in idx and xem_name(v) in idx): return   # máy khác vừa làm xong
    a = read_video(0, v, 1, ad, idx, t0)
    if a is None: jput(hong_name(v), {'loi': 'không đọc được'}, ad, idx); return
    if xem_name(v) not in idx:
        r = N.see([(1, a['name'], a['dur'], not v.get('broll'), (a.get('see') or {}).get('sheets', [])[:30])], log=log) if (a.get('see') or {}).get('sheets') else {1: {'tong': '', 'doan': []}}
        if 1 not in r: raise ClaudeWait('Claude chưa xem được video')
        jput(xem_name(v), r[1], ad, idx)
    log('  ✓ đọc + xem: %s › %s (%.1f phút)' % (jb['name'], v['name'], (time.time() - t0) / 60))

def style_of(jb):   # PHONG CÁCH KÊNH: Claude xem các video ĐÃ HẬU KỲ trước đó của kênh (nằm trong thư mục kênh, ngoài SOURCE) → bản mô tả phong cách để dựng theo
    try:
        src = get(jb['id'], 'id,parents'); chan = (src.get('parents') or [None])[0]
        if not chan: return ''
        ad, _ = ana_dir(); nm = '%s_phongcach.json' % chan; got = names_in(ad, [nm])
        if nm in got:
            try: return json.loads(raw(got[nm]).decode('utf-8')).get('mo_ta', '')
            except Exception: pass
        vids, st, seen = [], [chan], 0
        while st and seen < 60:
            d = st.pop(); seen += 1
            for c in kids(d):
                if c['mimeType'] == L.FOLDER:
                    if c['id'] == jb['id'] or re.search(r'\bsources?\b', L.norm1(c['name'])) or (c.get('appProperties') or {}).get('dungP') == '1' or SKIPDIR.match(nf(c['name'])): continue
                    st.append(c['id'])
                elif L.is_video(c) and int(c.get('size') or 0) < 3e9: vids.append(c)
        vids.sort(key=lambda c: c.get('createdTime') or '', reverse=True)
        imgs = []
        for k, v in enumerate(vids[:3]):
            try:
                a = L.analyze(900 + k, dict(id=v['id'], name=v['name'], size=int(v.get('size') or 0), dur=float((v.get('videoMediaMetadata') or {}).get('durationMillis') or 0) / 1000))
                import glob as _g
                ims = sorted(_g.glob(os.path.join(a.get('dir') or '', 'k*.jpg')))
                if ims: imgs += [('Video đã hậu kỳ "%s" – tờ %d:' % (v['name'], j + 1), sh['b']) for j, sh in enumerate(X.sheets(ims, a.get('kt') or [], per=16)[:2])]
            except Exception as e: log('  không xem được video mẫu', v['name'], e)
        if not imgs: return ''
        j = N.ask_json('Đây là các video kênh đã HẬU KỲ xong (thành phẩm team đã làm). Hãy mô tả PHONG CÁCH DỰNG để AI dựng các video mới THEO ĐÚNG phong cách này: bố cục khung, cỡ cảnh, nhịp cắt, kiểu chữ (font, cỡ, màu, vị trí, hiệu ứng, có khung/nền hay không), màu sắc / tông, chuyển cảnh, hiệu ứng, cách dùng cảnh phụ, logo / nhận diện, mở đầu và kết.\n'
                       'Trả JSON {"mo_ta":"mô tả ngắn gọn, cụ thể, dạng gạch đầu dòng, ≤ 1200 chữ"}', imgs, model='sonnet', key='mo_ta', log=log)
        if not j: return ''
        jput(nm, {'mo_ta': j['mo_ta'], 'videos': [v['name'] for v in vids[:3]]}, ad, {})
        log('  đã học phong cách kênh từ %d video đã hậu kỳ' % min(3, len(vids)))
        return j['mo_ta']
    except ClaudeWait: raise
    except Exception as e: log('  không học được phong cách kênh:', e); return ''

def do_plan(jb, key, models):
    jb = load(jb); ad, idx = idx_now(); engine()
    olds = [c['name'] for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s' and trashed=false" % L.FOLDER, 'name,appProperties')
            if str((c.get('appProperties') or {}).get('dungS', '')).startswith(jb['id'] + ':') and (c.get('appProperties') or {}).get('dungL') != LV]
    hint = ('CHỦ YÊU CẦU DỰNG LẠI (giữ đúng chủ đề, làm tốt hơn) các video đã giao: %s. Đưa các chủ đề này vào danh sách kịch bản trước.\n\n' % '; '.join(olds)) if olds else ''
    sty = style_of(jb)
    if sty: hint = 'PHONG CÁCH KÊNH (học từ các video đã hậu kỳ trước đó – dựng THEO phong cách này):\n' + sty + '\n\n' + hint
    scs = plan(jb, key, models, hint)
    for n, sc in enumerate(scs, 1): sc['_n'] = n
    jput('%s_kichban.json' % jb['id'], {'scripts': scs, 'phong_cach': sty}, ad, idx)
    log('  ✓ lên kịch bản: %s – %d kịch bản (lưu lại, không lên lại)' % (jb['name'], len(scs)))
    try: L.tsay('📖 AI ĐÃ ĐỌC XONG & PHÂN TÍCH SOURCE\n📁 %s\n🎬 %d video · ra %d kịch bản:\n%s\n➡️ Bắt đầu tự dựng các project' % (
        path_of(jb['id']), len(jb['A']), len(scs), '\n'.join('• %s' % (sc.get('ten') or '') for sc in scs)))
    except Exception as e: log('  không báo được Zalo:', e)

def do_build(jb, n):
    t0 = time.time(); jb = load(jb); ad, idx = idx_now(); engine(); codes(jb)
    book = jget('%s_kichban.json' % jb['id'], idx) or {}; stt = jget(st_name(jb, n), idx) or {}
    if stt.get('done') or int(stt.get('tries') or 0) >= MAXT: return   # máy khác vừa làm xong
    old = {}
    if not stt:   # lấy lại chỗ Claude đã sửa ở các kiểu dựng trước (mới nhất trước)
        for nm_ in ['%s_kb%d_L%d.json' % (jb['id'], n, v) for v in range(int(LV) - 1, 2, -1)] + ['%s_kb%d.json' % (jb['id'], n)]:
            old = jget(nm_, idx) or {}
            if old.get('sc'): break
    sc = stt.get('sc') or old.get('sc') or next(x for x in book['scripts'] if x['_n'] == n)
    jb['fixed'] = None; jb['qa_rej'] = 0
    try: r = publish(jb, sc, n)
    except ClaudeWait: raise
    except Exception as e: r = None; log('  ✗ kịch bản', n, e)
    if r:
        stt.update(done=True); jput(st_name(jb, n), stt, ad, idx)
        log('  ✓ %s (%.0fs) – %.1f phút' % (r['proj'], r['dur'], (time.time() - t0) / 60))
        if not r.get('exists'):
            try: link = (L.ix(link=r['id']) or {}).get('link') or L.SITE + '/_mo/' + r['id']   # link mở thẳng project trên web MICC media
            except Exception: link = L.SITE + '/_mo/' + r['id']
            mm, ss = divmod(int(time.time() - t0), 60)
            L.tsay('✅ AI DỰNG XONG PROJECT – ĐÃ ĐẨY LỐI TẮT\n🎬 %s (%d giây)\n⏱ Dựng mất %d phút %02d giây\n🔗 %s' % (r['proj'], r['dur'], mm, ss, link),
                   photo=(L.SITE + '/xt/' + r['thumb'] + '?w=480') if r.get('thumb') else None)   # ảnh thumbnail: khung hình người nói của project
        return
    stt['tries'] = int(stt.get('tries') or 0) + 1
    if not jb.get('qa_rej'): stt['tries'] = MAXT; log('  kịch bản %d không dựng được (thiếu câu / quá ngắn) – bỏ qua' % n)
    if jb.get('fixed'): stt['sc'] = jb['fixed']   # giữ chỗ Claude đã sửa → lần sau sửa tiếp, không làm lại từ đầu
    jput(st_name(jb, n), stt, ad, idx)
    log('  kịch bản %d chưa đạt (lần %d/%d) – sẽ dựng / sửa tiếp' % (n, stt['tries'], MAXT))

MARK = 'MICC - nhận diện ổ Drive (không xóa).txt'
def mark_root():   # file đánh dấu ở gốc "Drive của tôi" của tài khoản tailieumkt → công cụ đồng bộ nhận ra đúng ổ Drive của tài khoản này trên mỗi máy
    try:
        if not lq("'root' in parents and name='%s'" % MARK, 'id'):
            put(MARK, 'root', 'Ổ Drive có file này = Drive của tài khoản MICC (tailieumkt). Công cụ đồng bộ CapCut dùng nó để nối video vào project. Đừng xóa.'.encode('utf-8'), 'text/plain')
    except Exception as e: log('  không tạo được file nhận diện ổ Drive:', e)
def fix_public():   # project dựng lúc thử đường dẫn C:/Users/Public/MICC Drive → về đường dẫn Drive chuẩn (công cụ đồng bộ đổi tiếp theo ổ từng máy)
    try:
        for f in lq("(name='draft_content.json' or name='draft_info.json') and fullText contains 'MICC Drive'", 'id,name'):
            t = raw(f['id']).decode('utf-8')
            if 'C:/Users/Public/MICC Drive' in t: update(f['id'], t.replace('C:/Users/Public/MICC Drive', DRV).encode('utf-8'), 'application/json'); log('  sửa đường dẫn project (bỏ C:/Users/Public)')
    except Exception as e: log('  không sửa được đường dẫn cũ:', e)
def setup_bat():   # đưa bản mới của công cụ đồng bộ CapCut lên SETUP (máy người dùng tự lấy bản mới mỗi 2 phút)
    try:
        import hashlib
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'capcut', 'dong-bo-capcut.bat')
        if not os.path.exists(src): return
        data = open(src, 'rb').read(); md = hashlib.md5(data).hexdigest()
        st = lq("'%s' in parents and name='SETUP' and mimeType='%s'" % (L.ROOT, L.FOLDER), 'id')
        if not st: return
        f = lq("'%s' in parents and name='Cài đặt đồng bộ CapCut.bat'" % st[0]['id'], 'id,md5Checksum')
        if f and f[0].get('md5Checksum') == md: return
        for x in f:   # chủ dặn: xoá file cũ trước rồi mới đưa file mới (ngày tạo = lúc cập nhật, không nhầm bản cũ)
            try: L.drive('files/' + x['id'], {'trashed': True}, method='PATCH')
            except Exception: pass
        put('Cài đặt đồng bộ CapCut.bat', st[0]['id'], data, 'application/octet-stream')
        time.sleep(5)   # nhiều máy cùng đưa lên → giữ đúng 1 bản (bản tạo sau cùng), xoá bản trùng
        f = sorted(lq("'%s' in parents and name='Cài đặt đồng bộ CapCut.bat'" % st[0]['id'], 'id,createdTime'), key=lambda x: (x['createdTime'], x['id']))
        for x in f[:-1]:
            try: L.drive('files/' + x['id'], {'trashed': True}, method='PATCH')
            except Exception: pass
        log('  đã cập nhật công cụ đồng bộ CapCut trong SETUP')
    except Exception as e: log('  không cập nhật được công cụ đồng bộ:', e)

def rename_old():   # chủ dặn: mọi project AI dựng đổi tên "🤖 Tên dự án - Nội dung" (cả các project đã giao)
    try:
        for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s'" % L.FOLDER, 'id,name,parents,appProperties'):
            if c['name'].startswith((AI_ICON, XM)): continue
            par = (c.get('parents') or [''])[0]; new = safe(full_name(path_of(par), c['name']), 110)
            if not lock(c['id'], 'dungRN'): continue
            old = nf(c['name']); ren(c, par, new); unlock(c['id'], 'dungRN')
            log('  đổi tên project:', old, '→', new)
    except Exception as e: log('  không đổi được tên project cũ:', e)

def fix_vol():   # chủ dặn 11/11: SFX + nhạc nền 0 dB (không giảm âm lượng, không tự hạ khi có lời) – sửa cả project đã giao
    try:
        for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s'" % L.FOLDER, 'id,name,appProperties'):
            if (c.get('appProperties') or {}).get('dungVol') == '1' or not lock(c['id'], 'dungVL'): continue
            for f in lq("'%s' in parents and (name='draft_content.json' or name='draft_info.json')" % c['id'], 'id,name'):
                try:
                    d = json.loads(raw(f['id']).decode('utf-8')); ch = 0
                    for t in d.get('tracks') or []:
                        if t.get('type') != 'audio': continue   # chủ dặn: mọi âm thanh (lời, nhạc, hiệu ứng) 0 dB
                        for sg in t.get('segments') or []:
                            sg['volume'] = 1.0; sg['last_nonzero_volume'] = 1.0
                            sg['common_keyframes'] = [k for k in sg.get('common_keyframes') or [] if k.get('property_type') != 'KFTypeVolume']; ch += 1
                    if ch: update(f['id'], json.dumps(d, ensure_ascii=False).encode('utf-8'), 'application/json')
                except Exception as e: log('  âm lượng: không sửa được', c['name'], e)
            L.mark(c['id'], dungVol='1', dungVL=None); log('  âm lượng 0 dB:', c['name'])
    except Exception as e: log('  không sửa được âm lượng project cũ:', e)

RT = 'r6'   # đợt thu hồi (chủ dặn 11/11 chiều): thu hồi mọi project AI dựng (chưa bị người dùng sửa) rồi dựng lại bằng bản mới nhất
def retract_all():
    try:
        fid = list_file()
        if (get(fid, 'appProperties').get('appProperties') or {}).get('dungRT') == RT or not lock(fid, 'dungRTL'): return
        kept, gone, rem = [], 0, []
        for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s' and trashed=false" % L.FOLDER, 'id,name,parents,appProperties,createdTime'):
            par = (c.get('parents') or [''])[0]; rel = path_of(par) + '/' + nf(c['name'])
            if (c.get('appProperties') or {}).get('dungL') == LV: continue
            if user_edited(c): kept.append(nf(c['name'])); continue
            try: L.drive('files/' + c['id'], {'trashed': True}, method='PATCH'); rem.append(rel); gone += 1
            except Exception as e: log('  thu hồi lỗi', c['name'], e)
        for x in [x.strip() for x in raw(fid).decode('utf-8-sig').splitlines() if x.strip()]:   # bản Center Avenue (dựng tay trước đây) – chủ cho thu hồi
            if '/CapCut - Center Avenue' in x:
                par = '/'.join(x.split('/')[:-1]); nm = x.split('/')[-1]
                try:
                    host = next((f['id'] for f in lq("name='%s' and mimeType='%s'" % (par.split('/')[-1].replace("'", "\\'"), L.FOLDER), 'id,parents') if path_of(f['id']) == par), None)
                    for c in (lq("'%s' in parents and name='%s' and mimeType='%s'" % (host, nm.replace("'", "\\'"), L.FOLDER), 'id') if host else []):
                        L.drive('files/' + c['id'], {'trashed': True}, method='PATCH'); gone += 1
                    rem.append(x)
                except Exception as e: log('  thu hồi Center Avenue lỗi', nm, e)
        if rem: list_edit(remove=rem)
        L.mark(fid, dungRT=RT, dungRTL=None)
        log('  đã thu hồi %d project AI dựng%s' % (gone, ('; giữ %d project người dùng đã sửa: %s' % (len(kept), '; '.join(kept))) if kept else ''))
        try: L.tsay('♻️ ĐÃ THU HỒI %d PROJECT AI DỰNG – đang dựng lại bằng bản mới nhất, xong cái nào báo cái đó%s' % (gone, ('\n(giữ nguyên %d project anh/chị đã chỉnh sửa)' % len(kept)) if kept else ''))
        except Exception: pass
    except Exception as e: log('  không thu hồi được:', e)

def heal_list():   # danh sách CapCut luôn đúng với các project AI dựng đang có trên Drive
    try: list_edit(); log('  đã làm mới danh sách CapCut')
    except Exception as e: log('  không làm mới được danh sách CapCut:', e)

def pending():
    if PAUSE: heal_list(); setup_bat(); L.rtok(); return 0   # đang tạm dừng: vẫn giữ danh sách CapCut đúng
    for k in range(3):
        try: return len(tasks())
        except Exception as e: log('AI dựng: không quét được, thử lại', e); time.sleep(60)
    return 1

def run(key, models, until):
    if PAUSE: heal_list(); setup_bat(); L.rtok(); log('AI dựng: đang tạm dừng (chờ Google mở lại hạn mức tải của tài khoản)'); return
    os.makedirs(L.TMP, exist_ok=True)   # đọc lại từ bộ nhớ đệm thì chưa ai tạo thư mục tạm
    mark_root(); fix_public(); retract_all(); rename_old(); fix_vol(); heal_list(); setup_bat()
    idle, done_n, T, tT = 0, 0, [], 0
    while time.time() < until - 15 * 60 and not newer_code():
        if not T or time.time() - tT > 300:   # quét lại Drive tối đa 5 phút / lần (quét cả kho tốn ~1 phút)
            try: T = tasks(); tT = time.time()
            except Exception as e: log('AI dựng: quét lỗi', e); time.sleep(60); continue
        got = None
        while T:
            pr, kind, jb, x = T.pop(0)
            fid, k = (jb['id'], 'dungLock') if kind == 'plan' else ((x['id'], 'dungRL') if kind == 'read' else (idx_now()[1]['%s_kichban.json' % jb['id']], 'L%d' % x))
            if lock(fid, k): got = (kind, jb, x, fid, k); break
        if not got:
            T = []
            idle += 1
            if idle >= 2: log('AI dựng: hết việc cho máy này'); break
            time.sleep(60); continue
        idle = 0; kind, jb, x, fid, k = got
        log('AI dựng [%s] %s: %s' % (WID, {'read': 'ĐỌC', 'plan': 'LÊN KỊCH BẢN', 'build': 'DỰNG'}[kind], jb['name'] + (' › ' + x['name'] if kind == 'read' else (' › kịch bản %d' % x if kind == 'build' else ''))))
        try:
            if kind == 'read': do_read(jb, x)
            elif kind == 'plan': do_plan(jb, key, models)
            else: do_build(jb, x)
            done_n += 1
        except ClaudeWait as e:
            log('⏸', e); unlock(fid, k); break   # hết hạn mức Claude → dừng, lượt sau làm tiếp
        except Exception as e:
            log('✗ AI dựng lỗi (%s):' % kind, e)
            if kind == 'plan': L.mark(jb['id'], dungFail=(int(jb['ap'].get('dungFail') or 0) if jb['ap'].get('dungFailV') == DV else 0) + 1, dungFailV=DV, dungErr=str(e)[:100])
        unlock(fid, k)
    log('AI dựng [%s]: xong %d việc' % (WID, done_n))
