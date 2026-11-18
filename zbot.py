# Bot Zalo – bộ não Claude chạy trên GitHub (chủ dặn 18/11): lấy câu hỏi từ máy chủ, hỏi Claude Code (gói Max của chủ), gửi câu trả lời về máy chủ để bot đăng vào Zalo
import os, sys, json, urllib.request
API, S, JID = os.environ['MICC_API'], os.environ['MICC_SECRET'], os.environ.get('ZBOT_ID', '')
def call(action, **kw):
    req = urllib.request.Request(API, data=json.dumps(dict(kw, action=action, s=S)).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
def main():
    if not JID: return
    j = (call('zbotGet', id=JID) or {}).get('job')
    if not j: print('không còn câu hỏi (đã trả lời / quá hạn)'); return
    import nao as N
    sysp = (j.get('sys') or '') + '\n\nTrả lời NGAY bằng tiếng Việt, ngắn gọn, đúng trọng tâm, đúng giọng bot mô tả ở trên. Không dùng markdown. Chỉ dựa vào dữ liệu được cung cấp cho các câu về team / kho / công việc.'
    txt = None
    try: txt = N.ask(j.get('user') or '', model='opus', sys_p=sysp, timeout=240)
    except Exception as e: print('Claude lỗi:', repr(e)[:200])
    r = call('zbotDone', id=JID, text=txt or '', fail=0 if txt else 1)
    print('gửi về máy chủ:', r)
if __name__ == '__main__': main()
