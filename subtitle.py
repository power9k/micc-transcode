import json, os, re, subprocess, sys, time, urllib.request
API, S = os.environ.get('MICC_API', ''), os.environ.get('MICC_SECRET', '')
G = 'https://www.googleapis.com'
TMP = '/tmp/micc_sub'; os.makedirs(TMP, exist_ok=True)
WHISPER = os.environ.get('WHISPER_MODEL', 'large-v3-turbo')
LLM_REPO, LLM_FILE = 'Qwen/Qwen2.5-7B-Instruct-GGUF', 'qwen2.5-7b-instruct-q4_k_m.gguf'
BUDGET = time.time() + 60 * float(os.environ.get('SUB_MIN') or 300)
LANGS = {'vi': 'Tiếng Việt', 'en': 'English', 'zh': '中文', 'ja': '日本語', 'ko': '한국어', 'fr': 'Français', 'th': 'ไทย'}
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def api(action, **b):
    body = json.dumps(dict(action=action, s=S, host=os.environ.get('MICC_HOST', ''), **b)).encode()
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, data=body, method='POST'), timeout=180) as r: j = json.loads(r.read().decode())
            if j.get('ok') is False: raise RuntimeError(j.get('error'))
            return j
        except Exception:
            if i == 3: raise
            time.sleep(3 * (i + 1))
def ts(t):
    h, r = divmod(max(t, 0), 3600); m, s = divmod(r, 60)
    return '%02d:%02d:%06.3f' % (h, m, s)
def cues(segs):
    out = []
    for s in segs:
        txt = re.sub(r'\s+', ' ', s['t']).strip()
        if not txt: continue
        parts = [txt]
        if len(txt) > 84:
            words, cur, parts = txt.split(' '), '', []
            for w in words:
                if len(cur) + len(w) + 1 > 80 and cur: parts.append(cur); cur = w
                else: cur = (cur + ' ' + w).strip()
            if cur: parts.append(cur)
        dur, n = s['e'] - s['s'], sum(len(p) for p in parts) or 1
        t = s['s']
        for p in parts:
            d = dur * len(p) / n; out.append({'s': t, 'e': t + d, 't': p}); t += d
    return out
# Phụ đề từ bản 236: 1 phụ đề đúng lời nói (nhận ngôn ngữ theo từng câu, lẫn Anh – Việt vẫn đúng), có dấu câu + viết hoa, ngắt theo câu / cụm ý, mỗi câu tối đa 3 giây (cố dài gần 3 giây)
SUB_MAX = 3.0
PROMPT = 'Xin chào các bạn, hôm nay chúng ta cùng xem dự án mới nhé. Okay, let\'s go! Rất đẹp, đúng không?'
PUN_END, PUN_MID = re.compile(r'[.!?…]["”’)]*$'), re.compile(r'[,;:]["”’)]*$')
def cap_words(ws):
    up = True
    for w in ws:
        t = w['w'].strip()
        if up and t: w['w'] = re.sub(r'^(\W*)(\w)', lambda m: m.group(1) + m.group(2).upper(), w['w'], count=1)
        if t: up = bool(PUN_END.search(t))
    return ws
def cues_w(ws):
    txt = lambda l: re.sub(r'\s+([,.!?;:…])', r'\1', ' '.join(x['w'].strip() for x in l)).strip()
    sents, cur = [], []
    for w in ws:  # 1) tách theo câu (dấu kết câu hoặc ngừng nói > 1 giây)
        if cur and w['s'] - cur[-1]['e'] > 1.0: sents.append(cur); cur = []
        cur.append(w)
        if PUN_END.search(w['w'].strip()): sents.append(cur); cur = []
    if cur: sents.append(cur)
    parts = []
    dur = lambda l: l[-1]['e'] - l[0]['s']
    for sw in sents:  # 2) giữ TRỌN câu / ý: câu ≤ 4,5 giây giữ nguyên; dài hơn thì tách ở dấu phẩy thành các ý, ghép ý ngắn liền nhau ≤ 3 giây; ý nào > 6 giây mới chia đều
        if dur(sw) <= 4.5 and len(txt(sw)) <= 90: parts.append(sw); continue
        cl, cur = [], []
        for w in sw:
            cur.append(w)
            if PUN_MID.search(w['w'].strip()): cl.append(cur); cur = []
        if cur: cl.append(cur)
        merged = []
        for c in cl:
            if merged and dur(merged[-1] + c) <= SUB_MAX and len(txt(merged[-1] + c)) <= 84: merged[-1] = merged[-1] + c
            else: merged.append(c)
        for c in merged:
            if dur(c) <= 6 and len(txt(c)) <= 90: parts.append(c); continue
            n = max(2, -(-int(dur(c) * 100) // int(SUB_MAX * 100))); k = -(-len(c) // n)
            parts += [c[a:a + k] for a in range(0, len(c), k)]
    out = []
    for p in parts:  # 3) gộp các câu ngắn liền nhau cho gần 3 giây (≤ 3 giây, ≤ 2 dòng)
        if out and p[-1]['e'] - out[-1][0]['s'] <= SUB_MAX and p[0]['s'] - out[-1][-1]['e'] < .6 and len(txt(out[-1] + p)) <= 70 and PUN_END.search(out[-1][-1]['w'].strip()): out[-1] = out[-1] + p
        else: out.append(p)
    out = [{'s': p[0]['s'], 'e': p[-1]['e'], 't': txt(p)} for p in out]
    for i, c in enumerate(out):  # giữ chữ thêm chút cho dễ đọc, không đè câu sau, không quá 3 giây
        nxt = out[i + 1]['s'] if i + 1 < len(out) else c['e'] + 1
        c['e'] = max(c['e'], min(max(c['s'] + SUB_MAX, c['e']), nxt - .05, c['e'] + .5))
    return out
def punct(llm, ws):
    # thêm dấu câu + viết hoa khi bản chép lời thiếu; chỉ nhận kết quả nếu GIỮ ĐÚNG từng chữ (so sau khi bỏ dấu câu, chữ thường)
    norm = lambda t: re.sub(r'[^\w]', '', t.lower())
    B = 120
    for i in range(0, len(ws), B):
        ch = ws[i:i + B]; src = ' '.join(x['w'].strip() for x in ch)
        try:
            r = llm.create_chat_completion(messages=[{'role': 'system', 'content': 'Bạn thêm dấu câu (chấm, phẩy, chấm hỏi, chấm than) và viết hoa đúng chuẩn cho văn bản chép lời (có thể lẫn nhiều thứ tiếng). TUYỆT ĐỐI giữ nguyên từng chữ và thứ tự, không thêm, bớt, sửa hay dịch chữ nào. Chỉ trả về văn bản đã thêm dấu.'}, {'role': 'user', 'content': src}], max_tokens=len(src) + 400, temperature=0)['choices'][0]['message']['content'].strip()
        except Exception as e: log('   thêm dấu lỗi:', e); continue
        out = r.split()
        if [norm(x) for x in out if norm(x)] != [norm(x['w']) for x in ch if norm(x['w'])] or len(out) != len(ch): continue
        for w, t in zip(ch, out): w['w'] = ' ' + t
    return ws
def vtt(cs): return 'WEBVTT\n\n' + '\n\n'.join('%s --> %s\n%s' % (ts(c['s']), ts(c['e']), c['t']) for c in cs) + '\n'
def translate(llm, cs, lang):
    out, B = [], 25
    for i in range(0, len(cs), B):
        chunk = cs[i:i + B]
        src = '\n'.join('%d. %s' % (k + 1, c['t']) for k, c in enumerate(chunk))
        msg = [{'role': 'system', 'content': 'Bạn là biên dịch viên phụ đề video chuyên nghiệp. Dịch từng dòng phụ đề sang tiếng Việt tự nhiên, đúng ngữ cảnh, ngắn gọn như phụ đề phim; giữ tên riêng, thương hiệu. Trả về ĐÚNG số dòng, mỗi dòng dạng "số. bản dịch", không giải thích.'},
               {'role': 'user', 'content': 'Ngôn ngữ gốc: %s\n%s' % (lang, src)}]
        got = {}
        try:
            r = llm.create_chat_completion(messages=msg, max_tokens=60 * len(chunk) + 200, temperature=0.2)['choices'][0]['message']['content']
            for line in r.split('\n'):
                m = re.match(r'\s*(\d+)[.)]\s*(.+)', line)
                if m: got[int(m.group(1))] = m.group(2).strip()
        except Exception as e: log('   dịch lỗi:', e)
        for k, c in enumerate(chunk):
            t = got.get(k + 1)
            if not t:
                try: t = llm.create_chat_completion(messages=[msg[0], {'role': 'user', 'content': 'Ngôn ngữ gốc: %s\n1. %s' % (lang, c['t'])}], max_tokens=120, temperature=0.2)['choices'][0]['message']['content'].split('\n')[0]; t = re.sub(r'^\s*\d+[.)]\s*', '', t).strip()
                except Exception: t = c['t']
            out.append({'s': c['s'], 'e': c['e'], 't': t or c['t']})
    return out
ST = {'asr': None, 'llm': None}
def model():
    if ST['asr'] is None:
        try: api('ghLog', m='Phụ đề: đang tải mô hình chép lời')
        except Exception: pass
        from faster_whisper import WhisperModel
        ST['asr'] = WhisperModel(WHISPER, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 4)
    return ST['asr']
def do_job(job, token):
    wav = os.path.join(TMP, job['id'] + '.wav')
    try:
        url = '%s/drive/v3/files/%s?alt=media&supportsAllDrives=true' % (G, job['id'])
        pr = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-headers', 'Authorization: Bearer %s\r\n' % token, '-i', url, '-vn', '-ac', '1', '-ar', '16000', wav], capture_output=True, text=True, timeout=3600)
        if pr.returncode != 0:
            err = (pr.stderr or '').strip()[-300:]
            if re.search(r'does not contain any stream|matches no streams|no audio', err, re.I):
                api('subSave', id=job['id'], lang='und', orig='WEBVTT\n\n', vi='WEBVTT\n\n'); log('  ∅', job['name'], '(video không có tiếng)'); return True
            raise RuntimeError('ffmpeg: ' + err)
        kw = dict(language=None, vad_filter=True, beam_size=5, condition_on_previous_text=False, temperature=0, word_timestamps=True, initial_prompt=PROMPT)
        try: it, info = model().transcribe(wav, multilingual=True, **kw)  # nhận ngôn ngữ theo từng đoạn: video nói lẫn Anh – Việt vẫn chép đúng từng tiếng
        except TypeError: it, info = model().transcribe(wav, **kw)
        ws = []
        for sg in it:
            for w in (sg.words or []):
                if w.word.strip(): ws.append({'s': w.start, 'e': w.end, 'w': w.word})
        lang = info.language or 'und'
        if not ws: api('subSave', id=job['id'], lang=lang, orig='WEBVTT\n\n', vi=''); log('  ∅', job['name'], '(không có lời thoại)'); return True
        if sum(1 for w in ws if re.search(r'[.!?,…]', w['w'])) * 14 < len(ws):  # thiếu dấu câu → nhờ mô hình ngôn ngữ thêm dấu (giữ nguyên chữ)
            try:
                if ST['llm'] is None:
                    from llama_cpp import Llama
                    from huggingface_hub import hf_hub_download
                    ST['llm'] = Llama(model_path=hf_hub_download(LLM_REPO, LLM_FILE), n_ctx=8192, n_threads=os.cpu_count() or 4, verbose=False)
                ws = punct(ST['llm'], ws)
            except Exception as e: log('  ! thêm dấu lỗi, giữ bản chép lời:', e)
        cs = cues_w(cap_words(ws))
        api('subSave', id=job['id'], lang=lang, orig=vtt(cs), vi='')
        try: api('ghLog', m='✓ Phụ đề xong: ' + job['name'])
        except Exception: pass
        log('  ✓', job['name'], '·', lang, '·', len(cs), 'câu'); return True
    except Exception as e:
        log('  ✗', job['name'], e)
        try: api('subSave', id=job['id'], fail=str(e)[:200], dead=1 if re.search(r'Invalid data found|moov atom|could not find codec|End of file', str(e), re.I) else 0)
        except Exception: pass
        return False
    finally:
        try: os.remove(wav)
        except Exception: pass
def daemon():
    for line in sys.stdin:
        line = line.rstrip('\n')
        if not line: continue
        jid, _, name = line.partition('\t')
        ok = False
        try: ok = do_job({'id': jid, 'name': name or jid}, api('pxToken')['token'])
        except Exception as e: log('  ✗', name, e)
        print(('DONE ' if ok else 'FAIL ') + jid, flush=True)
def main():
    if not API or not S: sys.exit('Thiếu MICC_API hoặc MICC_SECRET')
    if os.environ.get('SUB_DAEMON'): return daemon()
    j = api('subJobs', n=2); jobs = j.get('jobs') or []
    if not jobs: log('Không có video nào cần phụ đề ✓'); return
    while jobs and time.time() < BUDGET:
        for job in jobs: do_job(job, j['token'])
        j = api('subJobs', n=2); jobs = j.get('jobs') or []
if __name__ == '__main__':
    main()
