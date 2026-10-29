"""MICC media · chép lời ghi âm trong bình luận + tóm tắt ngắn (chạy trên máy GitHub, miễn phí, không giới hạn)
- Whisper (faster-whisper) nghe tiếng Việt → toàn văn lời thoại
- Qwen2.5 (llama.cpp) tóm tắt thành 1 câu ngắn cho báo cáo Zalo
Kết quả gửi về máy chủ (Apps Script) để lưu vào bình luận trên Google Sheet."""
import json, os, sys, time, urllib.request
API, S = os.environ.get('MICC_API', ''), os.environ.get('MICC_SECRET', '')
G = os.environ.get('DRIVE_BASE', 'https://www.googleapis.com')
TMP = os.environ.get('TMP_DIR', '/tmp/micc_tr'); os.makedirs(TMP, exist_ok=True)
WHISPER = os.environ.get('WHISPER_MODEL', 'large-v3-turbo')
LLM_REPO = os.environ.get('LLM_REPO', 'Qwen/Qwen2.5-3B-Instruct-GGUF')
LLM_FILE = os.environ.get('LLM_FILE', 'qwen2.5-3b-instruct-q4_k_m.gguf')
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def api(action, **b):
    body = json.dumps(dict(action=action, s=S, host=os.environ.get('MICC_HOST', ''), **b)).encode()
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, data=body, method='POST'), timeout=120) as r:
                j = json.loads(r.read().decode())
            if j.get('ok') is False: raise RuntimeError(j.get('error'))
            return j
        except Exception as e:
            if i == 3: raise
            time.sleep(2 * (i + 1))
def download(fid, token, dst):
    req = urllib.request.Request(f'{G}/drive/v3/files/{fid}?alt=media&supportsAllDrives=true', headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=300) as r, open(dst, 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
SYS = ('Bạn là trợ lý của team làm video. Hãy tóm tắt lời góp ý bên dưới thành MỘT câu tiếng Việt ngắn gọn (tối đa 35 từ), '
       'giữ đủ các ý chỉnh sửa chính, viết như ghi chú công việc, không mở đầu kiểu "Người nói", không thêm ý mới, không dùng ngoặc kép.')
def main():
    if not API or not S: sys.exit('Thiếu MICC_API hoặc MICC_SECRET')
    j = api('trJobs', n=10)
    jobs = j.get('jobs') or []
    if not jobs: log('Không có ghi âm nào cần chép lời ✓'); return
    log('Có', len(jobs), 'bản ghi âm cần chép lời')
    from faster_whisper import WhisperModel
    asr = WhisperModel(WHISPER, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 4)
    llm = None
    try:
        from llama_cpp import Llama
        from huggingface_hub import hf_hub_download
        llm = Llama(model_path=hf_hub_download(LLM_REPO, LLM_FILE), n_ctx=4096, n_threads=os.cpu_count() or 4, verbose=False)
    except Exception as e:
        log('Không mở được mô hình tóm tắt, sẽ dùng câu đầu của lời thoại:', e)
    while jobs:
        for job in jobs:
            src = os.path.join(TMP, job['id'])
            try:
                download(job['id'], j['token'], src)
                segs, info = asr.transcribe(src, language=None, vad_filter=True, beam_size=5, condition_on_previous_text=False, temperature=0)
                text = ' '.join(s.text.strip() for s in segs).strip()
                summ = ''
                if text and llm:
                    out = llm.create_chat_completion(messages=[{'role': 'system', 'content': SYS}, {'role': 'user', 'content': text[:6000]}], max_tokens=140, temperature=0.2)
                    summ = out['choices'][0]['message']['content'].strip().strip('"“”').split('\n')[0]
                if text and not summ: summ = (text[:160] + '…') if len(text) > 160 else text
                api('trReport', id=job['id'], text=text, sum=summ)
                log('  ✓', job.get('name', job['id']), '→', summ[:90])
            except Exception as e:
                log('  ✗', job.get('name', job['id']), e)
                try: api('trReport', id=job['id'], fail=str(e)[:300])
                except Exception: pass
            finally:
                try: os.remove(src)
                except Exception: pass
        j = api('trJobs', n=10); jobs = j.get('jobs') or []
if __name__ == '__main__':
    main()
