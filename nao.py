# BỘ NÃO CLAUDE (bản nâng cấp lớn 11/2026) – chỉ dùng token Claude (gói Max của chủ), tiết kiệm tối đa:
#  - gọi thẳng 1 lượt, ảnh đưa trực tiếp (không qua công cụ Read), lời nhắc hệ thống ngắn → không tốn ~15k token khung Claude Code mỗi lần
#  - Sonnet: XEM tờ ảnh mẫu (mọi khung hình chính) → nhật ký hình ảnh từng đoạn (lưu Drive, không xem lại)
#  - Opus: lên kịch bản (chỉ chữ: lời + nhật ký hình + nhãn âm thanh) và KIỂM TRA bản dựng trước khi giao (xem ảnh xem trước)
#  - hết hạn mức → ClaudeWait: dừng, đợi lượt sau; KHÔNG tự làm theo luật
import os, re, json, time, subprocess, base64, io, math
import loc as L

class ClaudeWait(Exception): pass
_OK = []
# NHIỀU TÀI KHOẢN CLAUDE, 1 BỘ NÃO: cùng mô hình, cùng lời dặn – chỉ thêm hạn mức. Mỗi máy ưu tiên 1 tài khoản (chia đều), tài khoản nào hết hạn mức thì chuyển sang tài khoản kia.
TOKS = [t.strip() for t in (os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', ''), os.environ.get('CLAUDE_CODE_OAUTH_TOKEN_2', ''), os.environ.get('CLAUDE_CODE_OAUTH_TOKEN_3', '')) if t.strip()]
_W = int(re.sub(r'\D', '', os.environ.get('WORKER', '1')) or 1)
TOKS = TOKS[_W % len(TOKS):] + TOKS[:_W % len(TOKS)] if TOKS else TOKS
_BLOCK = {}
def ready():
    if _OK: return _OK[0]
    ok = False
    if TOKS:
        if not subprocess.run('command -v claude', shell=True, capture_output=True).stdout:
            subprocess.run('npm install -g @anthropic-ai/claude-code >/dev/null 2>&1', shell=True, timeout=300)
        ok = bool(subprocess.run('command -v claude', shell=True, capture_output=True).stdout)
    _OK.append(ok); return ok

USED = {}   # model → số lượt gọi (ghi vào nhật ký)
def ask(text, images=(), model='opus', sys_p='Bạn là editor video ngắn chuyên nghiệp. Trả lời bằng tiếng Việt, chỉ đúng định dạng được yêu cầu.', timeout=1800, log=print):
    """1 lượt hỏi Claude; images = [(chú thích, base64 jpeg)]. Trả chuỗi kết quả, None nếu lỗi, ném ClaudeWait nếu hết hạn mức."""
    if not ready(): raise ClaudeWait('chưa có Claude trên máy chạy')
    content = []
    for cap, b in images:
        if cap: content.append({'type': 'text', 'text': cap})
        content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b}})
    content.append({'type': 'text', 'text': text})
    msg = json.dumps({'type': 'user', 'message': {'role': 'user', 'content': content}}, ensure_ascii=False)
    live = [t for t in TOKS if _BLOCK.get(t, 0) < time.time()]
    if not live: raise ClaudeWait('mọi tài khoản Claude đang hết hạn mức tạm thời')
    for k, tok in enumerate(live):
        try:
            res = _ask1(msg, model, sys_p, timeout, log, tok)
            if res is None and k + 1 < len(live): continue   # tài khoản này lỗi (vd gói Pro không có mô hình này) → thử tài khoản kia
            return res
        except ClaudeWait as e:
            _BLOCK[tok] = time.time() + 30 * 60
            if k + 1 < len(live): log('  tài khoản Claude %d hết hạn mức → chuyển tài khoản khác' % (TOKS.index(tok) + 1)); continue
            raise
def _ask1(msg, model, sys_p, timeout, log, tok):
    try:
        r = subprocess.run(['claude', '-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose', '--model', model,
                            '--tools', '', '--strict-mcp-config', '--system-prompt', sys_p], input=msg + '\n', capture_output=True, text=True,
                           timeout=timeout, cwd=getattr(L, 'TMP', '/tmp'), env=dict(os.environ, CLAUDE_CODE_OAUTH_TOKEN=tok))
    except subprocess.TimeoutExpired: log('  Claude quá giờ'); return None
    res, err, used = None, False, []
    for ln in r.stdout.splitlines():
        try: j = json.loads(ln)
        except Exception: continue
        if j.get('type') == 'result':
            res, err = j.get('result'), j.get('is_error'); used = list((j.get('modelUsage') or {}).keys())
    for m in used: USED[m] = USED.get(m, 0) + 1
    blob = (res or '') + (r.stderr or '')[-500:]
    if (err or res is None) and re.search(r'(?i)usage limit|rate.?limit|limit reached|quota|overloaded|429|try again later|reset', blob):
        raise ClaudeWait('Claude hết hạn mức tạm thời: ' + blob[:160])
    if err or res is None: log('  Claude lỗi:', blob[:300]); return None
    log('  Claude (%s) đã trả lời' % (','.join(used) or model))
    return res

def ask_json(text, images=(), model='opus', key=None, tries=2, log=print, **kw):
    for k in range(tries):
        out = ask(text if not k else text + '\n\nLẦN TRƯỚC TRẢ SAI ĐỊNH DẠNG. Chỉ trả 1 khối JSON hợp lệ, không chữ nào khác.', images, model, log=log, **kw)
        o = out or ''; dec = json.JSONDecoder(); err = None
        for m in re.finditer(r'\{', o):   # đọc khối JSON đầu tiên hợp lệ, bỏ chữ thừa phía sau
            try: j, _ = dec.raw_decode(o[m.start():])
            except Exception as e: err = err or e; continue
            if isinstance(j, dict) and (key is None or key in j): return j
        if err: log('  JSON hỏng:', err)
    return None

# ---------------------------------------------------------------- 1) Sonnet XEM source: nhật ký hình ảnh từng đoạn
VSYS = ('Bạn là trợ lý dựng phim, xem tờ ảnh mẫu của video source (mỗi ô = 1 khung hình chính, góc trái ô ghi giây). '
        'Ghi lại CHÍNH XÁC những gì thấy, ngắn gọn, tiếng Việt. Chỉ trả JSON.')
def see(videos, log=print):
    """videos = [(số #, tên, độ dài, có lời?, [sheet...])] → {số #: [{s,e,canh,noi_dung,chat_luong,diem}]}"""
    imgs, head = [], []
    for i, nm, dur, talk, sh in videos:
        head.append('VIDEO #%d "%s" · %.1f giây · %s · %d tờ ảnh' % (i, nm, dur, 'người nói (A-roll)' if talk else 'cảnh phụ (B-roll)', len(sh)))
        for k, s in enumerate(sh): imgs.append(('#%d tờ %d/%d (%.1f–%.1fs):' % (i, k + 1, len(sh), s['ts'][0], s['ts'][-1]), s['b']))
    q = ('\n'.join(head) + '\n\nVới TỪNG video, chia thành các đoạn liền nhau theo nội dung hình (mỗi đoạn 1–8 giây, phủ hết video) và trả:\n'
         '{"videos":[{"video":<số #>,"tong":"1 câu tóm tắt video","doan":[{"s":giây,"e":giây,"canh":"cận/trung/toàn/flycam/chi tiết/…",'
         '"noi_dung":"ai/cái gì, đang làm gì, chuyển động máy (≤20 chữ)",'
         '"chat_luong":"tốt / rung / mờ nét / lóa / tối / nhìn lệch máy / ngập ngừng / vướng người qua / chữ-logo lạ …",'
         '"diem":1–10 (độ đẹp, dùng được để dựng)}]}]}\n'
         'Người nói: ghi rõ đoạn nào nhìn thẳng máy, đoạn nào quay đi, cười, ra hiệu cắt. Cảnh phụ: ghi rõ đoạn nào máy chạy mượt, đẹp nhất.')
    j = ask_json(q, imgs, model='sonnet', key='videos', sys_p=VSYS, log=log)
    out = {}
    for v in (j or {}).get('videos', []):
        try: out[int(v.get('video'))] = dict(tong=v.get('tong', ''), doan=v.get('doan') or [])
        except Exception: pass
    return out

def vlog_text(vl, k=40):
    if not vl: return '(chưa có nhật ký hình)'
    rows = ['  %.1f–%.1fs [%s] %s · %s · %s/10' % (float(d.get('s', 0)), float(d.get('e', 0)), d.get('canh', ''), d.get('noi_dung', ''), d.get('chat_luong', ''), d.get('diem', '?'))
            for d in sorted(sorted(vl.get('doan', []), key=lambda d: -float(d.get('diem') or 0))[:k], key=lambda d: float(d.get('s', 0)))]   # k đoạn đẹp nhất, theo thứ tự thời gian
    return 'Hình: ' + (vl.get('tong') or '') + '\n' + '\n'.join(rows)

def sound_text(runs):
    keep = [r for r in runs or [] if r[2] not in ('giọng nói', 'âm nền nhỏ')]
    return ('Âm thanh: ' + '; '.join('%d–%ds %s' % tuple(r) for r in keep[:25])) if keep else 'Âm thanh: chỉ giọng nói / âm nền nhỏ'

def faces_text(fc, dur):
    if not fc: return 'Mặt người: không thấy mặt rõ'
    ys = sorted(f[2] for f in fc); xs = sorted(f[1] for f in fc); sz = sorted(f[3] for f in fc)
    return 'Mặt người: thấy ở %d/%s khung chính, tâm mặt ~ (%.0f%% ngang, %.0f%% dọc), mặt rộng ~%.0f%% khung' % (
        len(fc), '?', 100 * xs[len(xs) // 2], 100 * ys[len(ys) // 2], 100 * sz[len(sz) // 2])

# ---------------------------------------------------------------- 2) mặt người → máy quay bám mặt + chữ né mặt
def face_at(a, t):
    fc = (a.get('see') or {}).get('faces') or []
    near = [f for f in fc if abs(f[0] - t) <= 1.6]
    if not near: return None
    near.sort(key=lambda f: abs(f[0] - t)); f = near[0]
    return f[1:]   # cx, cy, w, h (0–1 trên khung gốc)
def face_span(a, s, e):
    fc = [f for f in (a.get('see') or {}).get('faces') or [] if s - .5 <= f[0] <= e + .5]
    if not fc: return None
    med = lambda k: sorted(f[k] for f in fc)[len(fc) // 2]
    return med(1), med(2), med(3), med(4)

# ---------------------------------------------------------------- 3) nhịp nhạc: bám cắt / chuyển cảnh / giật zoom vào kick, snare, drop
def snap(t, pts, win=.22):
    if not pts: return t
    b = min(pts, key=lambda p: abs(p - t))
    return b if abs(b - t) <= win else t

# ---------------------------------------------------------------- 4) ảnh xem trước bản dựng (từ tờ ảnh mẫu) để Claude tự kiểm tra
def _tile(a, t):
    from PIL import Image
    best = None
    for s in (a.get('see') or {}).get('sheets') or []:
        for k, tt in enumerate(s['ts']):
            if best is None or abs(tt - t) < best[0]: best = (abs(tt - t), s, k)
    if not best: return None
    _, s, k = best
    im = Image.open(io.BytesIO(base64.b64decode(s['b']))).convert('RGB')
    x, y = (k % s['cols']) * s['tw'], (k // s['cols']) * s['th']
    t = im.crop((x, y, x + s['tw'], y + s['th']))
    t.paste(t.crop((0, 17, 54, 34)), (0, 0))   # che nhãn giây của tờ ảnh mẫu (không phải chữ trong video gốc)
    return t
def preview(pl, A_by_key, times, fontdir=None):
    """dựng khung xem trước 9:16 tại các mốc: hình (đã zoom theo keyframe) + chữ đúng vị trí → tờ ảnh 4 cột"""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 288, 512; tiles = []
    FK = {'BIG': 'SVN-Nexa Rush Sans Black.ttf', 'BEB': 'UTM Bebas.ttf', 'SCR': 'SVN-Dancing script.ttf', 'ITA': 'SVN-Georgia Italic.ttf'}
    def font(sz, fk='BIG'):
        p = os.path.join(fontdir or '', FK.get(fk, FK['BIG']))
        if fontdir and os.path.exists(p): return ImageFont.truetype(p, sz)
        try: return ImageFont.truetype('DejaVuSans-Bold.ttf', sz)
        except Exception: return ImageFont.load_default()
    for t in times:
        cv = Image.new('RGB', (W, H), (0, 0, 0))
        sh = next((s for s in sorted(pl['shots'], key=lambda s: s['line'] == 'A') if s['t0'] <= t < s['t1']), None)
        if sh:
            a = A_by_key.get(sh['media']); src = sh['src'] + (t - sh['t0'])
            im = _tile(a, src) if a else None
            if im is not None:
                ks = sh['keys']; k = ks[0]
                for p, q in zip(ks, ks[1:]):
                    if p[0] <= t <= q[0]:
                        r = (t - p[0]) / max(1e-6, q[0] - p[0]); k = [p[0]] + [p[j] + (q[j] - p[j]) * r for j in range(1, 5)]
                m, u, v = k[1], k[2], k[3]
                iw, ih = im.size; sc = max(W / iw, H / ih) * m; im2 = im.resize((max(1, int(iw * sc)), max(1, int(ih * sc))))
                ox = int(W / 2 - u * im2.width); oy = int(H / 2 - v * im2.height)
                ox = min(0, max(W - im2.width, ox)); oy = min(0, max(H - im2.height, oy)); cv.paste(im2, (ox, oy))
        dr = ImageDraw.Draw(cv)
        for ti in pl['titles']:
            if ti['t0'] <= t < ti['t1']:
                y = H * ti['y_pct'] / 100; n = len(ti['lines'])
                for j, (tx, fk, cap, col) in enumerate(ti['lines']):
                    f = font(max(9, int(H * cap / 100 * .55)), fk)
                    w = dr.textlength(tx, font=f); yy = y + (j - (n - 1) / 2) * H * .05
                    dr.text(((W - w) / 2, yy - f.size / 2), tx, font=f, fill=col or '#FFFFFF', stroke_width=1, stroke_fill='#000000')
        dr.rectangle([0, 0, 46, 13], fill=(0, 0, 0)); dr.text((2, 1), '%.1fs' % t, fill=(255, 230, 80))
        tiles.append(cv)
    out = []
    for g in range(0, len(tiles), 8):
        grp = tiles[g:g + 8]; rows = math.ceil(len(grp) / 4); sh = Image.new('RGB', (4 * W, rows * H), (20, 20, 20))
        for k, im in enumerate(grp): sh.paste(im, ((k % 4) * W, (k // 4) * H))
        b = io.BytesIO(); sh.save(b, 'JPEG', quality=60); out.append(base64.b64encode(b.getvalue()).decode())
    return out

# ---------------------------------------------------------------- 5) Opus KIỂM TRA bản dựng trước khi giao
QA_LIST = '''DANH SÁCH KIỂM TRA (chủ đã dặn, lỗi nào cũng phải sửa):
1. Chữ sai tên riêng / tên dự án (so với tên dự án chuẩn ở đầu dòng thời gian), sai chính tả / cụm vô nghĩa / không trọn nghĩa (vd "NINH VÀ", "TRƯỜNG SỐNG") / chữ không khớp lời đang nói / hiện sai lúc.
2. Chữ đè lên mặt người, chữ tràn khung, chữ chồng chữ.
3. Thiếu chữ (khoảng trống > 3 giây không có chữ) hoặc thừa (chữ dồn dập khó đọc, chép nguyên câu).
4. Cảnh phụ không khớp lời đang nói / vớ vẩn / không chuyên nghiệp, cảnh phụ xấu (rung, mờ, lóa, có người lạ, chữ in sẵn), cảnh lặp lại → đổi bằng doi_canh_phu (chọn đoạn đẹp, đúng ý lời nói trong KHO CẢNH PHỤ).
5. Cắt mất chữ / cắt giữa câu, câu nói lặp lại 2 lần, người nói ngập ngừng / nói hỏng / ra hiệu cắt còn sót.
6. Video đơn điệu: thiếu nhấn (zoom nhấn từ khóa, chuyển cảnh, hiệu ứng) hoặc lạm dụng hiệu ứng. ("giật zoom" ở từ khóa là CHỦ Ý nhấn nhá theo phong cách team – chỉ báo lỗi khi quá dày < 2 s/lần.)
7. Mở đầu không có câu hút (hook), kết thúc cụt / không có đoạn kết → gắn câu kết bằng them_cau (chọn trong danh sách CÂU KẾT); hook yếu → gắn câu hút lên đầu. Đổi nhân vật chính giữa chừng (người nói khác) là lỗi NẶNG → cat_doan đoạn đó.
8. Đè tiếng: 2 giọng nói cùng lúc, tiếng cảnh phụ lẫn vào lời, nhạc / SFX át giọng.
9. Lỗi font: ký tự hiện thành ô vuông / khối chữ nhỏ lạ, mất dấu tiếng Việt.
12. KHUNG HÌNH XẤU (lỗi NẶNG): khung cắt mất mặt / chỉ thấy cằm, ngực, cổ áo, tay; zoom quá cận; cảnh phụ là cận bộ phận cơ thể, bị cây lá che; ghép 2 khung chồng nhau rối mắt → bo_canh_phu (cảnh phụ) hoặc khung_rong [{"s":giây,"e":giây}] (cảnh người nói: về khung rộng, không zoom).
11. Bố cục chữ: chữ đè lên người / ngực trong khi phía trên đầu hoặc bên cạnh còn khoảng trống (phải đặt chữ vào khoảng trống); nhạc nền không hợp phong thái người nói / giọng kịch bản (vd nhạc da diết cho video năng động).
10. Video chán: ít hiệu ứng, cảnh đứng yên lâu, cảnh phụ không đa dạng, nhịp cắt đều đều không theo nhạc.'''
def qa(pl, timeline, pv_imgs, log=print, extra=''):
    q = (QA_LIST + '\n\nDÒNG THỜI GIAN BẢN DỰNG (mỗi mục chữ có số [T#], cảnh phụ có số [B#]):\n' + timeline + extra +
         '\n\nẢnh kèm theo = khung xem trước 9:16 của bản dựng tại các mốc (đúng vị trí chữ + khung hình đã zoom). '
         'Xem kỹ rồi trả JSON: {"dat":true/false,"loi":["mô tả ngắn từng lỗi"],'
         '"sua":{"bo_chu":[số T],"doi_chu":[{"T":số,"big":"chữ mới","small":"dòng phụ mới hoặc rỗng"}],"doi_vi_tri":[{"T":số,"y":phần trăm chiều cao 12–80}],'
         '"bo_canh_phu":[số B],"doi_canh_phu":[{"B":số,"video":số # trong KHO CẢNH PHỤ,"s":giây bắt đầu}],"doi_canh_tu_phu":[{"video":số # nguồn,"giay":giây gốc}],"phu_canh_phu":[{"s":giây timeline,"e":giây timeline,"video":số # trong KHO CẢNH PHỤ,"giay":giây bắt đầu}],"cat_doan":[{"s":giây timeline,"e":giây timeline}],"them_cau":[{"cau":"mã câu C…","vi_tri":"cuoi" hoặc "dau"}],"khung_rong":[{"s":giây timeline,"e":giây timeline}],"them_chu":[{"cau":"mã câu C…","tu":"chữ người nói (chép y nguyên)","big":"TỪ KHÓA","small":""}]}}\n'
         'Mỗi lỗi ghi mở đầu bằng [NẶNG] hoặc [NHẸ]. NẶNG = chữ sai nghĩa / sai chính tả / cụt nghĩa, chữ đè mặt, đang có lời mà hình không có người cũng không có cảnh phụ, '
         'cắt mất chữ / lặp câu / nói hỏng còn sót, cảnh hỏng (mờ, rung mạnh, đen) dài > 1 s, khoảng trống không chữ > 6 s, không có mở đầu hoặc kết cụt. '
         'Còn lại (hook có thể mạnh hơn, trống chữ 3–6 s, cảnh phụ chưa thật đẹp, chưa đa dạng…) là NHẸ. '
         'Ảnh xem trước nhỏ nên dấu tiếng Việt có thể nhòe: KHÔNG báo lỗi dấu trừ khi chắc chắn sai chữ.\n'
         'phu_canh_phu = PHỦ cảnh phụ lên đoạn đang có lời mà hình không có người / người chưa vào khung / khung xấu (giữ nguyên lời) – dùng cách này thay vì cat_doan khi lời vẫn cần; '
         'cat_doan = bỏ hẳn câu nói bị cắt hỏng / nói hỏng / lặp ở khoảng giây đó; doi_canh_tu_phu = đổi cảnh phụ tự phủ xấu (ghi số video # và giây gốc như trong dòng thời gian).\n'
         '"dat" = true khi KHÔNG còn lỗi NẶNG (lỗi NHẸ vẫn ghi vào "loi" và "sua" để sửa nếu được).')
    return ask_json(q, [('Xem trước %d:' % (k + 1), b) for k, b in enumerate(pv_imgs)], model='opus', key='dat',
                    sys_p='Bạn là trưởng nhóm kiểm duyệt video ngắn (TikTok/Reels) cực kỳ khó tính. Chỉ trả JSON.', log=log)
