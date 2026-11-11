# AI DỰNG PROJECT CAPCUT (bản 1, 10/11/2026) – chạy trên máy GitHub cùng lượt với loc.py
# Mỗi buổi quay (thư mục con của "Source"), từ MỚI đến CŨ, buổi mới tải lên được ưu tiên ngay sau buổi đang làm:
#  1) ĐỌC: xem hình (khung chính, độ nét/rung) + chép lời có mốc từng chữ – đọc song song với bước dựng
#  2) GEMINI (theo QUY TẮC DỰNG của chủ): tự chia kịch bản (mỗi video < 2 phút) nếu không có file kịch bản,
#     chọn câu nói hay nhất (đủ ý, đúng diễn xuất), cảnh phụ khớp lời, chữ nhấn ý chính
#  3) DỰNG: bỏ ngập ngừng / ầm à, che vết cắt bằng giật zoom, cảnh phụ, chữ, nhạc, hiệu ứng âm thanh → draft CapCut
#  4) Đưa project vào thư mục buổi quay (1 phiên bản duy nhất) + thêm vào MICC media · Hệ thống (không xóa)/AI dựng CapCut/Danh sách project CapCut.txt (máy nhân viên tự có lối tắt)
import os, sys, json, time, re, math, threading, queue, zipfile, base64, subprocess, unicodedata, urllib.request, urllib.parse
import loc as L
import xem as X, nao as N   # bản nâng cấp: X = mắt + tai (khung hình, mặt, âm thanh, nhạc), N = bộ não Claude

DV = '8'
LV = '2'   # kiểu dựng: 2 = nhiều lớp (A-roll / B-roll / màu / chữ / nhạc / SFX)                                   # đổi số này = dựng lại mọi buổi quay
EXCL = {'16rYEIREpSv2N78zOi5cOoLlXn5qHzGK4', '1RkqwSNXvzJ8XFnUYuvQlQlh_B0oYhnR-'}   # Center Avenue KB1, KB2: chủ đã duyệt tay
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
DRV = 'G:/Drive của tôi/PHÒNG TRUYỀN THÔNG MICC'   # đường dẫn lúc dựng; khi đưa lên Drive đổi sang ổ M: (máy nào công cụ đồng bộ cũng gán M: = thư mục này)
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
def raw(fid):
    req = urllib.request.Request(L.durl(fid), headers={'Authorization': 'Bearer ' + L.tok()})
    with urllib.request.urlopen(req, timeout=300) as r: return r.read()
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
    def one(iv):
        i, v = iv; br = bool(v.get('broll')); nm = '%s_%s%s_v2.json' % (v['id'], v.get('size') or 0, '' if br else '_loi')   # v2 = có tờ ảnh mọi khung chính + mặt + nhãn âm thanh
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
            log('  đọc video %d/%d: %s (%.1f phút từ đầu)' % (i + 1, len(vids), v['name'], (time.time() - t0) / 60))
        _MEM[nm] = a
        return dict(a, i=i + 1, vid=v)
    with ThreadPoolExecutor(3) as ex: A = [a for a in ex.map(one, enumerate(vids)) if a]
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
                req = urllib.request.Request(L.G + '/drive/v3/files/%s/export?mimeType=text/plain' % d['id'], headers={'Authorization': 'Bearer ' + L.tok()})
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
    parts = [{'text': extra + 'Kênh / dự án: %s\nBuổi quay: %s\nCó %d video.\n%s' % (path_of(jb['id']), jb['name'], len(jb['A']), doc_text(jb) or '(không có file kịch bản – tự phân tích)') + ('\nSource có các thư mục con "Kịch bản N": MỖI thư mục Kịch bản = đúng 1 video (1 script), A-roll lấy từ chính thư mục đó; thư mục khác = kho cảnh phụ dùng chung.' if jb.get('kbtop') else '\nTự phân tích toàn bộ source để chia các kịch bản, mỗi kịch bản 1 video dưới 2 phút.')}]
    C = jb['C'] = {}
    for a in jb['A']:
        head = '[thư mục: %s] ' % (jb.get('dn') or {}).get(a['vid'].get('dir'), '') + L.summary(a).split('\nLời thoại:')[0]
        head += '\n' + N.vlog_text(a.get('vlog')) + '\n' + N.sound_text((a.get('see') or {}).get('sound'))
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
def tighten(a, s, e):   # bỏ ngập ngừng: cắt ĐÚNG khoảng lặng giữa 2 từ, không cắt vào chữ
    W = [w for w in words(a, s, e) if L.norm(w[2]) not in L.FILL]
    if not W: return [(s, e)]
    iv = []
    for w in W:
        if iv and w[0] - iv[-1][1] <= .45: iv[-1][1] = w[1]
        else: iv.append([w[0], w[1]])
    out = []
    for k, (x, y) in enumerate(iv):
        lo = iv[k - 1][1] + .03 if k else s - .2
        hi = iv[k + 1][0] - .03 if k + 1 < len(iv) else e + .3
        x2, y2 = max(lo, x - .12), min(hi, y + .2)
        if y2 - x2 > .3: out.append((max(0.0, x2), min(y2, a['dur'] - .05)))
    return out
def grade_of(a):   # đo màu gốc của từng cảnh (khung mẫu) → thông số Điều chỉnh CapCut để ra màu điện ảnh: ấm nhẹ, tương phản, highlight dịu
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
        g = dict(brightness=c((.47 - m) * 1.1, -.25, .3),
                 contrast=c((.23 - sd) * 2.2 + .12, -.1, .5),                 # cảnh phẳng (log / trời mù) tăng tương phản mạnh hơn
                 highlight=c(-.12 - hi * 3, -.45, 0),                        # dịu vùng cháy sáng
                 shadow=c(-.08 if lo < .03 else .06, -.2, .2),               # đổ bóng sâu cho có khối, trừ khi đã quá tối
                 temperature=c(.1 - cast * 1.6, -.35, .35),                  # khử ám màu rồi đẩy ấm nhẹ kiểu điện ảnh
                 tone=c(-gm * 2.0, -.25, .25))                               # khử ám xanh lá / tím
        if sat < .12: g['white'] = c(.05, 0, .1)
        return g
    except Exception as e: log('  không đo được màu', a.get('name'), e); return {}
FX_TR = [('Pull in', '6724226861666144779'), ('Glare II', '6952697917563998722'), ('Flash', '6987208055511323137'), ('Pull out', '6724226338418332167')]
BMOVES = [((1.0, .5, .5, 0.0), (1.09, .5, .5, 0.0)), ((1.1, .5, .5, 0.0), (1.0, .5, .5, 0.0)), ((1.08, .44, .5, 0.0), (1.08, .56, .5, 0.0)),
          ((1.08, .56, .5, 0.0), (1.08, .44, .5, 0.0)), ((1.05, .5, .5, -1.2), (1.1, .5, .5, 1.2)), ((1.0, .5, .56, 0.0), (1.08, .5, .46, 0.0))]
def build_plan(jb, sc, proj, adir, music=None, mmap=None):
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
    t, pieces, why, n_sent = 0.0, [], {}, 0
    for ai, it in enumerate(sc.get('aroll', [])):
        a = A.get(vid(it.get('video', 0))); s, e = float(it.get('s', 0)), float(it.get('e', 0))
        if not a: why['sai số video'] = why.get('sai số video', 0) + 1; continue
        if a['vid'].get('broll'): why['chọn nhầm cảnh phụ'] = why.get('chọn nhầm cảnh phụ', 0) + 1; continue
        if e - s < .6: why['đoạn quá ngắn'] = why.get('đoạn quá ngắn', 0) + 1; continue
        e = min(e, a['dur'] - .05); base = 1.0 if n_sent % 2 == 0 else 1.2; n_sent += 1
        for j, (x, y) in enumerate(tighten(a, s, e)):
            d = y - x; k = key(a); m = base if j % 2 == 0 else round(base * 1.1, 3)
            f0, f1 = N.face_span(a, x, x + min(d, 1.5)), N.face_span(a, max(x, y - 1.5), y)   # bám mặt người nói (YuNet theo từng khung chính)
            m1 = round(m * (1 + min(.06, .018 * d)), 4)
            uv = lambda f, mm: (round(f[0], 3), round(min(.75, f[1] + .1 / mm), 3)) if f else (.5, .42)   # mặt nằm ở 1/3 trên khung
            u0, v0 = uv(f0, m); u1, v1 = uv(f1 or f0, m1)
            shots.append(dict(media=k, src=round(x, 3), t0=round(t, 3), t1=round(t + d, 3), line='A', face=f0 or f1,
                              keys=[[round(t, 3), m, u0, v0, 0.0], [round(t + d, 3), m1, u1, v1, 0.0]], punch_abs=[]))
            speech.append(dict(media=k, src_in=round(x, 3), t0=round(t, 3), t1=round(t + d, 3), vol=1.0))
            pieces.append((a['i'], x, y, t, ai)); t += d
        if t > 118: break
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
        titles.append(dict(t0=round(max(0, T - .04), 3), t1=round(min(total - .05, T + 2.2), 3), line='A', lines=lines, y_pct=y, bright=False, anim=n, si=si))
        if num: sfx.append(dict(file='SFX tit thong tin.wav', t=round(max(0, T - .02), 3), vol=.2, dur=0.34))   # tiếng "tít" khi thông tin / số liệu hiện
        elif n % 3 == 0: sfx.append(dict(file='SFX pop chu 02.wav', t=round(max(0, T - .02), 3), vol=.12, dur=0.180091))
        if n % 2 == 0 or num:
            for sh in shots:   # giật zoom đúng lúc nói từ khóa (cảnh người nói)
                if sh['line'] == 'A' and sh['t0'] + .2 < T < sh['t1'] - .35:
                    T = N.snap(T, beats, .12) if beats else T   # giật zoom trùng phách nếu phách ở rất gần từ khóa
                    k0, k1 = sh['keys'][0], sh['keys'][-1]; m = k0[1]
                    sh['keys'] = [k0, [round(T - .001, 3), m] + k0[2:], [round(T + .08, 3), round(m * 1.14, 4)] + k0[2:], [k1[0], round(m * 1.16, 4)] + k1[2:]]; break
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
        k = sh['keys'][0]; m = k[1]; lim = max(0.0, (m - 1) / (2 * m)); v = max(.5 - lim, min(.5 + lim, k[3]))   # engine giới hạn khung không lộ viền
        return (.5 + (f[1] - f[3] / 2 - v) * m) * 100, (.5 + (f[1] + f[3] / 2 - v) * m) * 100
    for z in titles:
        hh = sum(l[2] for l in z['lines']) * .75 + 2
        for T in (z['t0'] + .05, (z['t0'] + z['t1']) / 2):
            fc = face_canvas(T)
            if not fc or fc[1] < z['y_pct'] - hh / 2 - 1 or fc[0] > z['y_pct'] + hh / 2 + 1: continue
            below, above = fc[1] + hh / 2 + 3, fc[0] - hh / 2 - 3
            z['y_pct'] = round(below if below <= 76 else (above if above >= 14 else 76), 1); z['ne_mat'] = 1; break
    # ---- điểm dồn của nhạc (drop) → giật zoom mạnh đúng lúc nhạc dồn
    for dp in (mmap.get('drops') or [])[:2]:
        if 2 < dp < total - 2:
            sh = next((x for x in shots if x['t0'] + .2 < dp < x['t1'] - .3 and x['line'] == 'A' and len(x['keys']) == 2), None)
            if sh:
                k0, k1 = sh['keys']; m = k0[1]
                sh['keys'] = [k0, [round(dp - .001, 3), m] + k0[2:], [round(dp + .06, 3), round(m * 1.18, 4)] + k0[2:], [k1[0], round(m * 1.2, 4)] + k1[2:]]
    for i in range(len(titles) - 1): titles[i]['t1'] = min(titles[i]['t1'], round(titles[i + 1]['t0'] - .08, 3))
    sfx.insert(0, dict(file='SFX impact epic 01.wav', t=0.0, src_in=1.25, vol=.2, dur=5.144853))
    # ---- nhạc nền: mỗi project 1 bài riêng (chọn ở publish), lặp nếu ngắn
    MF = music or (('Nhac nen 06 - Rising Sun.mp3', 91.742041) if 'academy' in path_of(jb['id']).lower() or 'đào tạo' in jb['name'].lower() else ('Nhac nen 05 - Sparta.mp3', 104.045714))
    mus, mt = [], 0.0
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
    for a_, b_ in zip(ashots, ashots[1:]):   # khít liền, không hở
        if abs(a_['t1'] - b_['t0']) < .02: a_['t1'] = b_['t0']; a_['keys'][-1][0] = b_['t0']
    # SFX sinh động: whoosh khi cảnh phụ vào (cách nhau ≥ 2 s), "tách" nhẹ khi đổi cảnh phụ liền nhau
    wt = [x['t'] for x in sfx if 'whoosh' in x['file']]
    for k_, b in enumerate(bshots):
        prev = bshots[k_ - 1] if k_ else None
        if prev is not None and abs(prev['t1'] - b['t0']) < .01: continue
        if all(abs(b['t0'] - w) >= 2.0 for w in wt): sfx.append(dict(file='SFX whoosh mem.wav', t=max(0, round(b['t0'] - .22, 3)), vol=.22, dur=0.58)); wt.append(b['t0'])
    return dict(project=proj, out_dir=os.path.join(L.TMP, 'out'), asset_dir=adir, media=media, total=total, lines=[dict(id='A', t0=0.0, t1=total)],
                apieces=[[p[4], round(p[3], 3), round(p[3] + p[2] - p[1], 3)] for p in pieces], ashots=ashots, bshots=bshots, speech=speech, shots=shots, titles=titles, transitions=trans, effects=fx, music=mus, sfx=sorted(sfx, key=lambda x: x['t']), matte=[])


# ---------------------------------------------------------------- nhạc nền: mỗi project 1 bài KHÁC NHAU (ưu tiên nhạc chủ để trong thư mục buổi quay, rồi tới Kho nhạc nền)
def used_music(add=None):
    cd = cache_dir(); f = lq("'%s' in parents and name='Nhạc đã dùng.txt'" % cd, 'id')
    ids = [x for x in raw(f[0]['id']).decode('utf-8').splitlines() if x.strip()] if f else []   # lưu TÊN bài (bài trùng tên ở chỗ khác cũng coi là đã dùng)
    if add and add not in ids:
        ids.append(add); data = '\n'.join(ids).encode('utf-8')
        if f: update(f[0]['id'], data, 'text/plain')
        else: put('Nhạc đã dùng.txt', cd, data, 'text/plain')
    return ids
def pick_music(jb):
    try:
        AU = lambda d: [c for c in lq("'%s' in parents and mimeType contains 'audio/'" % d, 'id,name,size,mimeType') if int(c.get('size') or 0) > 800000
                        and not re.search(r'(?i)voice|vocal|giọng|giong|sfx|whoosh|lồng tiếng', c['name'])]
        local = [c for d in list(jb['dirs']) + [p[0] for p in jb.get('pool', [])] for c in AU(d)]
        kho = lq("'%s' in parents and name='Kho nhạc nền' and mimeType='%s'" % (cache_dir(), L.FOLDER), 'id')
        cands = local + (AU(kho[0]['id']) if kho else [])
        used = set(used_music()); fresh = [c for c in cands if nf(c['name']).lower() not in used] or cands
        if not fresh: return None
        c = fresh[0]; fp = os.path.join(L.TMP, 'nhac_' + c['id'])
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
def list_edit(add=(), remove=()):
    fid = list_file(); lines = [x.strip() for x in raw(fid).decode('utf-8-sig').splitlines() if x.strip()]
    lines = [x for x in lines if x not in remove] + [x for x in add if x not in lines]
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
    return '\n'.join(out)
def review(jb, sc, pl, proj, adir, mu):
    sc0 = sc
    A = {'V%d' % a['i']: a for a in jb['A']}
    for rnd in range(4):   # 1 lần kiểm + tối đa 3 lần sửa
        ts = sorted({round((z['t0'] + z['t1']) / 2, 2) for z in pl['titles']} | {round(x['t0'] + .3, 2) for x in pl['shots'] if x['line'] != 'A'})
        if len(ts) > 24: ts = ts[::math.ceil(len(ts) / 24)]
        try: pv = N.preview(pl, A, ts, os.path.join(ENG, 'fonts'))
        except Exception as e: pv = []; log('  không dựng được ảnh xem trước:', e)
        r = N.qa(pl, timeline(jb, sc, pl), pv, log=log)
        if r is None: raise ClaudeWait('Claude chưa kiểm tra được bản dựng')
        log('  kiểm tra vòng %d: %s%s' % (rnd + 1, 'ĐẠT' if r.get('dat') else 'chưa đạt', '' if r.get('dat') else ' – ' + '; '.join(map(str, r.get('loi') or []))[:400]))
        if r.get('dat'): return pl
        if rnd == 3: break
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
        for c in fx.get('doi_canh_tu_phu') or []:   # cảnh tự phủ xấu → không dùng đoạn đó nữa
            try: sc.setdefault('_bad', []).append([int(c['video']), float(c['giay'])])
            except Exception: pass
        bdrop = {int(x) for x in fx.get('bo_canh_phu') or [] if str(x).lstrip('-').isdigit()}
        sc['broll'] = [b for i, b in enumerate(sc.get('broll') or []) if i not in bdrop]
        pl2 = build_plan(jb, sc, proj, adir, (mu[1], mu[2]) if mu else None, mu[4] if mu else None)
        if not pl2 and fx.get('cat_doan') and aro0 is not None:   # bỏ câu làm video quá ngắn → giữ lại câu đó
            sc['aroll'] = aro0; pl2 = build_plan(jb, sc, proj, adir, (mu[1], mu[2]) if mu else None, mu[4] if mu else None)
        if not pl2: break
        pl = pl2
    log('  ✗ Claude kiểm tra chưa đạt sau 3 vòng sửa – KHÔNG giao project này:', proj); jb['qa_rej'] = jb.get('qa_rej', 0) + 1; jb.setdefault('rej_sc', []).append(sc0); return None
def publish(jb, sc, n):
    a0 = jb['A'][0]; A_ = {a['i']: a for a in jb['A']}; cnt = {}
    for it in sc.get('aroll', []):   # project nằm trong thư mục (Kịch bản N) chứa phần lớn câu nói của kịch bản
        c = (jb.get('C') or {}).get(str(it).strip().upper()) if isinstance(it, str) else None
        a = A_.get(c[0]) if c else A_.get(int(re.sub(r'\D', '', str(it.get('video', 0))) or 0)) if isinstance(it, dict) else None
        if a: d = (jb.get('kbtop') or {}).get(a['vid']['dir'], a['vid']['dir']); cnt[d] = cnt.get(d, 0) + 1
    host = max(cnt, key=cnt.get) if cnt else jb['id']
    proj = safe(re.sub(r'(?i)^(capcut|kịch bản|kich ban|kb)\s*\d*\s*[-–:]*\s*', '', sc.get('ten') or '') or '%s %d' % (jb['name'], n), 60)   # tên = nội dung, ngắn gọn
    rel = path_of(host) + '/' + proj; adir = DRV + '/' + rel + '/AI tải về'
    mu = pick_music(jb)
    pl = build_plan(jb, sc, proj, adir, (mu[1], mu[2]) if mu else None, mu[4] if mu else None)
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
    inhost = [c for c in lq("'%s' in parents and appProperties has { key='dungP' and value='1' } and trashed=false" % host, 'id,name,appProperties')]
    new_ = [c for c in inhost if (c.get('appProperties') or {}).get('dungL') == LV]
    old_ = [c for c in inhost if (c.get('appProperties') or {}).get('dungL') != LV]   # bản dựng kiểu cũ (1 track) → chủ dặn dựng lại rồi thay
    if host in set((jb.get('kbtop') or {}).values()) and new_:
        log('  thư mục này đã có project – giữ nguyên:', path_of(host)); return dict(proj=proj, dur=0, exists=True)   # mỗi thư mục Kịch bản 1 project
    slot = '%s:%d' % (jb['id'], n)
    if any((c.get('appProperties') or {}).get('dungS') == slot or c['name'] == proj for c in new_):
        log('  đã có project này trên Drive – giữ nguyên, không ghi đè:', proj); return dict(proj=proj, dur=0, exists=True)
    pf = mkdir(proj, host, {'dungP': '1', 'dungS': slot, 'dungL': LV})   # đánh dấu thư mục project (tên không còn chữ CapCut)
    try:
        af = mkdir('AI tải về', pf)
        for f in lq("'%s' in parents and trashed=false" % LIB, 'id,name,mimeType'):
            if f['name'].startswith(LIB_SKIP) or f.get('mimeType') == L.FOLDER: continue
            try: L.drive('files/%s/copy' % f['id'], {'name': f['name'], 'parents': [af]}, params={'fields': 'id'})
            except Exception:   # file bị chặn sao chép → tải về rồi đưa lên lại
                try: put(f['name'], af, raw(f['id']), f.get('mimeType') or 'application/octet-stream')
                except Exception as e: log('  bỏ file thư viện', f['name'], e)
        for fn in ('draft_content.json', 'draft_info.json', 'draft_meta_info.json'):
            put(fn, pf, to_m(open(os.path.join(od, fn), 'rb').read()), 'application/json')
        put('draft_cover.jpg', pf, base64.b64decode(a0['thumbs'][len(a0['thumbs']) // 2][1]), 'image/jpeg')
        if mu:
            try: L.drive('files/%s/copy' % mu[0], {'name': mu[1], 'parents': [af]}, params={'fields': 'id'})
            except Exception: put(mu[1], af, raw(mu[0]), 'audio/mpeg')
        list_edit(add=[rel])
        if mu: used_music(add=mu[3])
        for c in old_:   # bản mới đã lên xong → mới bỏ bản cũ (vào thùng rác Drive, khôi phục được)
            try:
                L.drive('files/' + c['id'], {'trashed': True}, method='PATCH'); list_edit(remove=[path_of(host) + '/' + c['name']])
                log('  đã thay bản cũ:', c['name'])
            except Exception as e: log('  không bỏ được bản cũ', c['name'], e)
    except Exception:   # hỏng giữa chừng → bỏ thư mục dở, không để rác
        try: L.drive('files/' + pf, {'trashed': True}, method='PATCH')
        except Exception: pass
        raise
    return dict(proj=proj, dur=pl['total'], url='https://drive.google.com/drive/folders/' + pf)

def edit(jb, key, models):
    t0 = time.time()
    tops = set((jb.get('kbtop') or {}).values())
    redo_nm = '%s_redo_v%s.json' % (jb['id'], DV); redo = None
    if redo_nm in (jb.get('idx') or {}):
        try: redo = json.loads(raw(jb['idx'][redo_nm]).decode('utf-8'))
        except Exception: redo = None
    if redo == []: log('  đã làm xong các kịch bản của thư mục này'); L.mark(jb['id'], dungV=DV, dungFail=None); return []
    if not redo and ((tops and all(lq("'%s' in parents and appProperties has { key='dungL' and value='%s' } and trashed=false" % (t, LV), 'id') for t in tops)) or
       lq("appProperties has { key='dungS' and value='%s:1' } and appProperties has { key='dungL' and value='%s' } and mimeType='%s' and trashed=false" % (jb['id'], LV, L.FOLDER), 'id')):
        log('  đã có project, bỏ qua:', jb['name']); L.mark(jb['id'], dungV=DV, dungFail=None); return []
    engine()
    if redo: codes(jb); log('  làm lại %d kịch bản bị kiểm duyệt loại lượt trước (không lên kế hoạch lại)' % len(redo))
    olds = [] if redo else [c['name'] for c in lq("appProperties has { key='dungP' and value='1' } and mimeType='%s' and trashed=false" % L.FOLDER, 'name,appProperties')
                            if str((c.get('appProperties') or {}).get('dungS', '')).startswith(jb['id'] + ':') and (c.get('appProperties') or {}).get('dungL') != LV]
    if olds: log('  dựng lại theo kiểu nhiều lớp:', ', '.join(olds))
    hint = ('CHỦ YÊU CẦU DỰNG LẠI (giữ đúng chủ đề, làm tốt hơn) các video đã giao: %s. Đưa các chủ đề này vào danh sách kịch bản trước.\n\n' % '; '.join(olds)) if olds else ''
    scs, done = (redo or (plan(jb, key, models, hint) if hint else plan(jb, key, models))), []
    for rnd in range(2):   # lần 2: Gemini chọn thiếu câu nói → hỏi lại 1 lần, nói rõ lỗi
        log('  Claude: %d kịch bản' % len(scs))
        for n, sc in enumerate(scs, 1):
            n = int(sc.get('_n') or n); sc['_n'] = n   # giữ đúng số kịch bản khi làm lại
            try:
                r = publish(jb, sc, n)
                if r: done.append(r); log('  ✓ %s (%.0fs) – %.1f phút' % (r['proj'], r['dur'], (time.time() - t0) / 60))
                if r and not r.get('exists'):
                    try: tot = len(lq("appProperties has { key='dungP' and value='1' } and mimeType='%s'" % L.FOLDER, 'id'))
                    except Exception: tot = 0
                    L.tsay('✅ AI DỰNG XONG PROJECT – ĐÃ ĐẨY LỐI TẮT\n🎬 %s (%d giây)\n📁 %s\n📊 Tổng đã hoàn thành: %d project\n💻 Mở CapCut là thấy (lối tắt tự vào máy trong ~2 phút)' % (r['proj'], r['dur'], path_of(jb['id']), tot))
            except Exception as e: log('  ✗ kịch bản', n, e)
        if done or not scs or rnd or jb.get('qa_rej'): break   # Claude kiểm tra đã loại → không lên lại trong lượt này (tránh tốn token), lượt sau làm tiếp
        log('  Claude chọn thiếu câu nói → hỏi lại')
        scs = plan(jb, key, models, 'LẦN TRƯỚC KẾ HOẠCH HỎNG: tổng A-roll dưới 15 giây. Lần này BẮT BUỘC chọn đủ 45–110 giây câu nói (số # của video CÓ LỜI THOẠI của buổi quay, không phải KHO CẢNH PHỤ; chỉ ghi MÃ CÂU C…).\n\n')
    rej = jb.get('rej_sc') or []
    nr = (int(jb['ap'].get('dungRej') or 0) if jb['ap'].get('dungFailV') == DV else 0) + 1
    if (redo is not None or rej) and jb.get('ad'):   # lưu kịch bản bị loại để lượt sau dựng lại (không gọi Opus lên kế hoạch lại)
        try: put(redo_nm, jb['ad'], json.dumps(rej if nr < 6 else [], ensure_ascii=False).encode('utf-8'), 'application/json')
        except Exception as e: log('  không lưu được kịch bản cần làm lại:', e)
    if rej and done and nr < 6:
        L.mark(jb['id'], dungRej=nr, dungFailV=DV, dungErr='còn %d kịch bản chờ làm lại' % len(rej))
        log('  còn %d kịch bản bị loại – lượt sau dựng lại (lần %d/6)' % (len(rej), nr)); return done
    if scs and not done and jb.get('qa_rej'):   # Claude kiểm tra loại hết → không tính là lỗi máy; tối đa 3 lượt rồi chờ người xem
        nr = (int(jb['ap'].get('dungRej') or 0) if jb['ap'].get('dungFailV') == DV else 0) + 1
        L.mark(jb['id'], dungRej=nr, dungFailV=DV, dungFail=3 if nr >= 6 else None, dungErr='Claude kiểm tra loại %d lần' % nr)
        log('  Claude kiểm tra loại hết kịch bản (lần %d/6) – lượt sau lên lại' % nr); return []
    if scs and not done: raise RuntimeError('không dựng được kịch bản nào – thử lại lượt sau')
    L.mark(jb['id'], dungV=DV, dungN=len(done), dungT=int(time.time()), dungFail=None)
    if False and done and len(done) > 1:   # chủ dặn: không gửi tổng kết, chỉ báo từng project kèm tổng số
        L.tsay('🎬 AI DỰNG XONG CẢ BUỔI QUAY: %d PROJECT CAPCUT\n📁 %s\n%s\n⏱ %.0f phút · mở CapCut là có (lối tắt tự vào máy)' % (
            len(done), path_of(jb['id']), '\n'.join('• %s (%d giây)' % (r['proj'], r['dur']) for r in done), (time.time() - t0) / 60))
    return done

# ---------------------------------------------------------------- vòng chạy: đọc trước 1 buổi trong lúc dựng buổi hiện tại
def pending():
    if PAUSE: return 0
    for k in range(3):
        try: return len(scan())
        except Exception as e: log('AI dựng: không quét được, thử lại', e); time.sleep(60)
    return 1   # quét lỗi mãi → vẫn giữ lượt chạy để run() thử lại, không bỏ việc
ONLY = ''   # bỏ trống ('') = chạy mọi thư mục source
PAUSE = False   # chủ dặn: tạm dừng giao project cho tới khi bản nâng cấp lớn (Claude xem dày khung hình, âm thanh, nhịp nhạc, tracking, tự kiểm tra) xong
def run(key, models, until):
    if PAUSE: log('AI dựng: đang tạm dừng chờ bản nâng cấp'); return
    os.makedirs(L.TMP, exist_ok=True)   # đọc lại từ bộ nhớ đệm thì chưa ai tạo thư mục tạm
    try: migrate_m()
    except Exception as e: log('AI dựng: đổi ổ M lỗi', e)
    q, busy = queue.Queue(maxsize=1), set()
    def reader():
        while time.time() < until - 20 * 60:
            try: J = [j for j in scan() if j['id'] not in busy]
            except Exception as e: log('AI dựng: quét lỗi', e); time.sleep(60); continue
            if not J: q.put(None); return
            jb = J[0]; busy.add(jb['id']); log('AI dựng – đọc:', jb['src'], '›', jb['name'], '(%d video)' % len(jb['vids']))
            try: q.put(read(jb))
            except ClaudeWait as e: log('⏸ đọc:', e); busy.discard(jb['id']); q.put(None); return   # hết hạn mức Claude → dừng, lượt sau đọc tiếp
            except Exception as e:
                log('  đọc lỗi:', e); L.mark(jb['id'], dungFail=(int(jb['ap'].get('dungFail') or 0) if jb['ap'].get('dungFailV') == DV else 0) + 1, dungFailV=DV, dungErr=str(e)[:100])
        q.put(None)
    th = threading.Thread(target=reader, daemon=True); th.start()
    built = [0]
    while True:
        jb = q.get()
        if jb is None: break
        try: built[0] += len([r for r in (edit(jb, key, models) or []) if not r.get('exists')])
        except ClaudeWait as e:
            log('⏸', e); L.mark(jb['id'], dungErr='chờ Claude'); break   # không tính là lỗi, lượt sau (10 phút / lần) làm tiếp
        except Exception as e:
            log('✗ AI dựng lỗi:', e); L.mark(jb['id'], dungFail=(int(jb['ap'].get('dungFail') or 0) if jb['ap'].get('dungFailV') == DV else 0) + 1, dungFailV=DV, dungErr=str(e)[:100])
            if (int(jb['ap'].get('dungFail') or 0) if jb['ap'].get('dungFailV') == DV else 0) + 1 >= 3: L.tsay('❌ AI DỰNG LỖI (đã thử 3 lần)\n📁 %s\n%s' % (jb['name'], str(e)[:300]))   # lỗi tạm thời tự thử lại, không báo ồn
    try:
        if built[0] and not scan():
            tot = len(lq("appProperties has { key='dungP' and value='1' } and mimeType='%s'" % L.FOLDER, 'id'))
            L.tsay('🏁 AI ĐÃ DỰNG HẾT CÁC THƯ MỤC SOURCE\n📊 Tổng đã hoàn thành: %d project' % tot)
    except Exception as e: log('  không báo được tổng:', e)
