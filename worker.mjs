import { spawn } from 'node:child_process';
import fs from 'node:fs';
const SV = process.env.SV_DIR || '/tmp/sv', HOST = process.env.MICC_HOST || '', API = process.env.MICC_API, S = process.env.MICC_SECRET, START = Date.now(), DEADLINE = START + (Number(process.env.MAX_MIN || 330)) * 60e3, HALF = START + (DEADLINE - START) * .5;
const TMP = process.env.TMP_DIR || '/tmp/micc', G = process.env.DRIVE_BASE || 'https://www.googleapis.com';
fs.mkdirSync(TMP, { recursive: true });
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function api(action, b = {}) {
  for (let i = 0; i < 4; i++) {
    try { const r = await fetch(API, { method: 'POST', body: JSON.stringify({ action, s: S, host: HOST, ...b }), redirect: 'follow' }); const j = await r.json(); if (j.ok === false) throw new Error(j.error || 'lỗi máy chủ'); return j; }
    catch (e) { if (i === 3) throw e; await sleep(2000 * (i + 1)); }
  }
}
const token = async () => (await api('pxToken')).token;
function run(cmd, args) { return new Promise((ok, no) => { const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] }); let out = '', err = ''; p.stdout.on('data', d => out += d); p.stderr.on('data', d => err += d); p.on('close', c => c === 0 ? ok(out) : no(new Error(cmd + ' lỗi: ' + err.slice(-400)))); }); }
async function download(id, size, dst) {
  let got = 0; if (fs.existsSync(dst)) fs.unlinkSync(dst);
  for (let tries = 0; tries < 8 && got < size; tries++) {
    try {
      const r = await fetch(G + '/drive/v3/files/' + id + '?alt=media&supportsAllDrives=true', { headers: { Authorization: 'Bearer ' + await token(), Range: 'bytes=' + got + '-' } });
      if (r.status !== 200 && r.status !== 206) throw new Error('Drive ' + r.status + ' ' + (await r.text()).slice(0, 200));
      if (r.status === 200 && got) { got = 0; fs.unlinkSync(dst); }
      const w = fs.createWriteStream(dst, { flags: 'a' });
      for await (const chunk of r.body) { if (!w.write(chunk)) await new Promise(o => w.once('drain', o)); got += chunk.length; }
      await new Promise(o => w.end(o));
    } catch (e) { log('  tải lỗi, thử lại:', e.message); await sleep(3000 * (tries + 1)); }
  }
  if (got < size) throw new Error('tải video gốc không đủ (' + got + '/' + size + ')');
}
async function encode(src, dst, h, w0, h0) {
  const portrait = w0 && h0 ? w0 < h0 : false;
  const vf = (portrait ? `scale=${h}:-2` : `scale=-2:${h}`) + ':flags=bicubic';
  await run('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-map', '0:v:0', '-map', '0:a:0?', '-vf', vf,
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', h <= 480 ? '27' : '24', '-maxrate', h <= 480 ? '1200k' : '2800k', '-bufsize', h <= 480 ? '2400k' : '5600k',
    '-pix_fmt', 'yuv420p', '-profile:v', 'main', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', h <= 480 ? '96k' : '128k', '-ac', '2', '-threads', '0', dst]);
}
async function upload(file, name, folder, ofId) {
  const size = fs.statSync(file).size;
  const init = await fetch(G + '/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true&fields=id', { method: 'POST',
    headers: { Authorization: 'Bearer ' + await token(), 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': String(size) },
    body: JSON.stringify({ name, parents: [folder], mimeType: 'video/mp4', appProperties: { pxOf: ofId } }) });
  if (!init.ok) throw new Error('mở phiên tải lên lỗi ' + init.status + ' ' + (await init.text()).slice(0, 200));
  const url = init.headers.get('location'), CH = 64 << 20, fd = fs.openSync(file, 'r');
  try {
    let pos = 0;
    while (pos < size) {
      const n = Math.min(CH, size - pos), buf = Buffer.alloc(n); fs.readSync(fd, buf, 0, n, pos);
      let r; for (let t = 0; t < 5; t++) { try { r = await fetch(url, { method: 'PUT', headers: { 'Content-Range': `bytes ${pos}-${pos + n - 1}/${size}` }, body: buf }); if (r.status < 500) break; } catch (e) {} await sleep(2000 * (t + 1)); }
      if (r.status === 200 || r.status === 201) return { id: (await r.json()).id, size };
      if (r.status !== 308) throw new Error('tải lên lỗi ' + r.status + ' ' + (await r.text()).slice(0, 200));
      const rg = r.headers.get('range'); pos = rg ? Number(rg.split('-')[1]) + 1 : pos + n;
    }
  } finally { fs.closeSync(fd); }
  throw new Error('tải lên chưa xong');
}
async function one(job, folder) {
  const src = TMP + '/src_' + job.id, t0 = Date.now();
  log('▶', job.name, '(' + Math.round(job.size / 1048576) + ' MB) cần', job.need.join('p, ') + 'p');
  await download(job.id, job.size, src);
  let w = job.w, hh = job.h;
  if (!w || !hh) { try { const o = JSON.parse(await run('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', src])); w = o.streams[0].width; hh = o.streams[0].height; } catch (e) {} }
  const short = Math.min(w || 1080, hh || 1080), need = job.need.filter(x => x < short).sort((a, b) => a - b);
  for (let i = 0; i < need.length; i++) {
    const h = need[i], out = TMP + '/out_' + job.id + '_' + h + '.mp4';
    await encode(src, out, h, w, hh);
    const up = await upload(out, job.name.replace(/\.[^.]+$/, '') + ' (' + h + 'p).mp4', folder, job.id);
    await api('pxReport', { id: job.id, pid: up.id, h, size: up.size, last: i === need.length - 1 });
    fs.unlinkSync(out); log('  ✓ ' + h + 'p xong', Math.round(up.size / 1048576) + ' MB');
  }
  if (!need.length) await api('pxReport', { id: job.id, fail: 'video nhỏ hơn 480p, không cần bản nhẹ' });
  try { fs.unlinkSync(src); } catch (e) {}
  log('  xong sau', Math.round((Date.now() - t0) / 1000) + 's');
}
const rlog = (m, lvl) => api('ghLog', { m, lvl }).catch(() => {});
async function main() {
  if (!API || !S) throw new Error('Thiếu MICC_API hoặc MICC_SECRET');
  await rlog('Bắt đầu lượt chạy (' + (process.env.GITHUB_EVENT_NAME || '?') + ')');
  let done = 0;
  while (Date.now() < DEADLINE - 20 * 60e3) {
    if (Date.now() > HALF) { let pk = {}; try { pk = await api('subJobs', { peek: 1 }); } catch (e) {} if (pk.left) { log('Đã dùng nửa thời gian cho bản nhẹ → chuyển sang phụ đề'); await rlog('Đã dùng nửa thời gian cho bản nhẹ → chuyển sang phụ đề'); break; } }
    const j = await api('pxJobs', { n: 2 });
    if (!j.jobs || !j.jobs.length) { log('Hết việc bản nhẹ ✓ (đã làm ' + done + ' video)'); break; }
    for (const job of j.jobs) {
      if (Date.now() > DEADLINE - 15 * 60e3) break;
      try { await one(job, j.folder); done++; } catch (e) { log('  ✗ lỗi:', e.message); try { await api('pxReport', { id: job.id, fail: e.message.slice(0, 300) }); } catch (x) {} }
    }
    log('… còn khoảng', j.left, 'video đang chờ');
  }
  if (Date.now() >= DEADLINE - 20 * 60e3) log('Gần hết giờ chạy, lượt sau làm tiếp. Đã làm', done, 'video');
  await subtitles();
}
const runP = (cmd, args, env) => new Promise((ok, no) => { const p = spawn(cmd, args, { stdio: 'inherit', env: Object.assign({}, process.env, env || {}) }); p.on('close', c => c === 0 ? ok() : no(new Error(cmd + ' thoát mã ' + c))); p.on('error', no); });
async function subtitles() {
  if (process.env.NO_SUB) return;
  const left = DEADLINE - Date.now() - 10 * 60e3; if (left < 15 * 60e3) return;
  let j; try { j = await api('subJobs', { peek: 1 }); } catch (e) { return log('Phụ đề: không hỏi được máy chủ', e.message); }
  if (!j.left) return log('Phụ đề: không có video nào cần làm ✓');
  log('Phụ đề: có', j.left, 'video cần làm → cài công cụ'); await rlog('Phụ đề: ' + j.left + ' video cần làm, đang cài công cụ');
  try {
    if (!fs.existsSync(SV + '/bin/python')) { await runP('python3', ['-m', 'venv', SV]); try { await runP(SV + '/bin/pip', ['install', '-q', '--prefer-binary', 'faster-whisper', 'huggingface_hub', 'llama-cpp-python', '--extra-index-url', 'https://abetlen.github.io/llama-cpp-python/whl/cpu']); } catch (e) { await rlog('Phụ đề: cài Qwen lỗi (' + e.message + ') → chỉ chép lời, không dịch', 'err'); await runP(SV + '/bin/pip', ['install', '-q', '--prefer-binary', 'faster-whisper', 'huggingface_hub']); } }
    await rlog('Phụ đề: cài xong, bắt đầu làm');
    await runP(SV + '/bin/python', ['subtitle.py'], { SUB_MIN: String(Math.floor((DEADLINE - Date.now() - 10 * 60e3) / 60e3)) });
  } catch (e) { log('Phụ đề lỗi:', e.message); await rlog('Phụ đề lỗi: ' + e.message, 'err'); }
}
main().catch(e => { console.error(e); process.exit(1); });
