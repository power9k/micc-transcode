# Tách giọng người bằng Demucs (htdemucs). Chạy nền: đọc từng dòng JSON {"src","voc","rest"} ở stdin,
# ghi file WAV giọng người (voc) và/hoặc phần còn lại không có giọng (rest), trả "DONE <src>" hoặc "FAIL <lỗi>".
import sys, json, subprocess, numpy as np, torch, soundfile as sf
from demucs.pretrained import get_model
from demucs.apply import apply_model
torch.set_num_threads(max(1, torch.get_num_threads()))
# Chỉ TÁCH (lọc bỏ) phần không phải giọng người, không tạo / sửa giọng. Đoạn lồng tiếng (ft) dùng bản htdemucs_ft tách sạch hơn.
M = get_model('htdemucs'); M.eval(); SR = M.samplerate; VI = M.sources.index('vocals'); MF = None
def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vn', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return torch.from_numpy(np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T.copy())
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        j = json.loads(line); w = load(j['src'])
        if w.shape[1] < SR // 4: raise ValueError('âm thanh quá ngắn')
        ref = w.mean(0); m, s = ref.mean(), ref.std() + 1e-8
        md = M
        if j.get('ft'):
            if MF is None: MF = get_model('htdemucs_ft'); MF.eval()
            md = MF
        with torch.no_grad(): out = apply_model(md, ((w - m) / s)[None], device='cpu', split=True, overlap=0.25, progress=False)[0] * s + m
        if j.get('voc'): sf.write(j['voc'], out[VI].T.numpy(), SR, subtype='PCM_16')
        if j.get('rest'): sf.write(j['rest'], (out.sum(0) - out[VI]).T.numpy(), SR, subtype='PCM_16')
        print('DONE ' + j['src'], flush=True)
    except Exception as e:
        print('FAIL ' + str(e).replace('\n', ' ')[:300], flush=True)
