# Bot Zalo – bộ não Claude chạy trên GitHub (chủ dặn 18/11). Máy bật sẵn liên tục (--serve) hỏi máy chủ có câu hỏi mới không → trả lời ngay bằng Claude Code (gói Claude của chủ) + ghi bộ nhớ riêng của bot
import os, sys, json, time, urllib.request, functools
print = functools.partial(print, flush=True)   # log hiện ngay trên GitHub
API, S = os.environ['MICC_API'], os.environ['MICC_SECRET']
def call(action, timeout=60, **kw):
    req = urllib.request.Request(API, data=json.dumps(dict(kw, action=action, s=S)).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
RULE = ('\n\nCÁCH TRẢ LỜI (chủ dặn): hiểu đúng người hỏi đang cần gì rồi đưa lại CHÍNH XÁC thứ đó, ngắn gọn, không lan man; có link thì đưa đúng link trong dữ liệu; '
        'dùng dữ liệu thật (file trong kho, bảng Nhiệm vụ, bộ nhớ riêng) – không bịa; được yêu cầu viết content / viết hộ thì viết đầy đủ, hay; biết rõ ai đang nói chuyện với mày (tên trong câu hỏi). '
        'Không dùng markdown. BỘ NHỚ: mọi thông tin đáng nhớ trong câu mới (vd nộp quỹ phòng / quỹ nhóm bao nhiêu, ai nợ ai, lịch, sở thích, quyết định, thông tin dự án…) phải ghi lại vào "nho" thật chi tiết (ai, chủ đề, nội dung đầy đủ, số tiền nếu có) để lần sau hỏi là trả lời được; câu hỏi tổng hợp (vd quỹ còn bao nhiêu, ai đã nộp) thì tự cộng trừ từ bộ nhớ cho chính xác. '
        'Trả về DUY NHẤT 1 khối JSON: {"tra_loi":"câu trả lời gửi vào nhóm Zalo","nho":[{"ai":"tên người","chu_de":"vd Quỹ nhóm","noi_dung":"chi tiết","so_tien":số hoặc null}]}')
def answer(j):
    import nao as N
    os.makedirs(getattr(N.L, 'TMP', '/tmp'), exist_ok=True)
    txt = mem = None
    try:
        fx = lambda t: str(t or '').encode('utf-16', 'surrogatepass').decode('utf-16', 'replace')   # emoji bị cắt đôi (nửa ký tự) → Claude báo UnicodeEncodeError (lỗi 18/11)
        r = N.ask_json(fx(j.get('user')), model='opus', sys_p=fx(j.get('sys')) + RULE, timeout=150)
        if isinstance(r, dict): txt, mem = r.get('tra_loi'), r.get('nho')
    except Exception as e: print('Claude lỗi:', repr(e)[:200])
    print('trả lời', j['id'], 'xong' if txt else 'LỖI', call('zbotDone', id=j['id'], text=txt or '', mem=mem or [], fail=0 if txt else 1))
def main():
    if '--serve' in sys.argv:   # bật sẵn tối đa ~5 giờ 40 phút (GitHub cho 6 giờ / lượt), lịch tự bật lại
        end = time.time() + 5.6 * 3600
        import nao as N
        os.makedirs(getattr(N.L, 'TMP', '/tmp'), exist_ok=True)   # thiếu thư mục làm việc → Claude báo FileNotFoundError (lỗi 18/11)
        import shutil; print('Claude sẵn sàng:', N.ready(), shutil.which('claude') or 'KHÔNG THẤY lệnh claude')
        while time.time() < end:
            try:
                r = call('zbotNext', timeout=150)
                if r.get('job'): print('nhận câu hỏi', r['job'].get('id'), 'của', r['job'].get('name')); answer(r['job'])
                elif r.get('error') or r.get('ok') is False: print('máy chủ báo:', str(r)[:200]); time.sleep(5)
            except Exception as e: print('hỏi máy chủ lỗi:', repr(e)[:160]); time.sleep(5)
        return
    jid = os.environ.get('ZBOT_ID', '')
    if jid:
        j = (call('zbotGet', id=jid) or {}).get('job')
        if j: answer(j)
        else: print('câu này máy bật sẵn đã nhận / quá hạn')
if __name__ == '__main__': main()
