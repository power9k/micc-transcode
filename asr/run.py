"""Word-level transcription for the Academy edits (runs on a GitHub runner, where the model hosts are reachable).
For every asr/requests/<name>.json without a result: pull the listed ranges of the original Drive file (public link,
closed byte ranges through rangeproxy.py), run faster-whisper with word timestamps, write asr/results/<name>.json.
Request: {"drive_id": "...", "ranges": [[start_s, end_s], ...], "model": "large-v3-turbo"}
Result:  {"drive_id": ..., "ranges": [...], "words": [{"w": "...", "s": abs_start, "e": abs_end, "p": prob}, ...]}"""
import glob, json, os, socket, subprocess, sys, time

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

todo = [p for p in sorted(glob.glob("asr/requests/*.json")) if not os.path.exists(p.replace("requests", "results"))]
if not todo: print("nothing to do"); sys.exit(0)
from faster_whisper import WhisperModel
models = {}
for req_path in todo:
    R = json.load(open(req_path)); t0 = time.time()
    name = R.get("model", "large-v3-turbo")
    if name not in models: models[name] = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    asr = models[name]
    port = free_port()
    proxy = subprocess.Popen([sys.executable, "asr/rangeproxy.py", R["drive_id"], str(port)], stdout=subprocess.PIPE, text=True)
    proxy.stdout.readline()
    words = []
    for a, b in R["ranges"]:
        a0 = max(0.0, a - 0.5)
        wav = "/tmp/asr_seg.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a0:.3f}", "-to", f"{b + 0.5:.3f}", "-i", f"http://127.0.0.1:{port}/v.mp4",
                        "-map", "0:a:0", "-ac", "1", "-ar", "16000", wav], check=True)
        segs, _ = asr.transcribe(wav, language="vi", word_timestamps=True, vad_filter=False, beam_size=5,
                                 condition_on_previous_text=False, temperature=0)
        for s in segs:
            for w in (s.words or []):
                words.append({"w": w.word.strip(), "s": round(a0 + w.start, 3), "e": round(a0 + w.end, 3), "p": round(w.probability, 3)})
    proxy.terminate()
    out = {"drive_id": R["drive_id"], "ranges": R["ranges"], "model": name, "words": words, "seconds": round(time.time() - t0, 1)}
    json.dump(out, open(req_path.replace("requests", "results"), "w"), ensure_ascii=False)
    print(f"{req_path}: {len(words)} words in {out['seconds']}s", flush=True)
