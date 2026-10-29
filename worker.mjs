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
class Preempt extends Error {}
const DEAD = /Invalid data found|moov atom not found|could not find codec|does not contain any stream/i;
const SKIP = [];
let CTX = null;
function run(cmd, args) { return new Promise((ok, no) => { const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] }), ctx = CTX; if (ctx) ctx.kids.add(p); let out = '', err = ''; p.stdout.on('data', d => out += d); p.stderr.on('data', d => err += d); p.on('close', c => { if (ctx) ctx.kids.delete(p); if (ctx && ctx.pre) return no(new Preempt()); c === 0 ? ok(out) : no(new Error(cmd + ' lỗi: ' + err.slice(-400))); }); }); }
async function download(id, size, dst) {
  let got = 0; if (fs.existsSync(dst)) fs.unlinkSync(dst);
  for (let tries = 0; tries < 8 && got < size; tries++) {
    try {
      if (CTX && CTX.pre) throw new Preempt();
      const r = await fetch(G + '/drive/v3/files/' + id + '?alt=media&supportsAllDrives=true', { headers: { Authorization: 'Bearer ' + await token(), Range: 'bytes=' + got + '-' }, signal: CTX && CTX.ac.signal });
      if (r.status !== 200 && r.status !== 206) throw new Error('Drive ' + r.status + ' ' + (await r.text()).slice(0, 200));
      if (r.status === 200 && got) { got = 0; fs.unlinkSync(dst); }
      const w = fs.createWriteStream(dst, { flags: 'a' });
      for await (const chunk of r.body) { if (!w.write(chunk)) await new Promise(o => w.once('drain', o)); got += chunk.length; }
      await new Promise(o => w.end(o));
    } catch (e) { if (CTX && CTX.pre) throw new Preempt(); log('  tải lỗi, thử lại:', e.message); await sleep(3000 * (tries + 1)); }
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
async function px(job, folder) {
  const src = TMP + '/src_' + job.id;
  log('  ▶ bản nhẹ', job.need.join('p, ') + 'p (' + Math.round(job.size / 1048576) + ' MB)');
  try {
    await download(job.id, job.size, src);
    let w = job.w, hh = job.h;
    if (!w || !hh) { try { const o = JSON.parse(await run('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', src])); w = o.streams[0].width; hh = o.streams[0].height; } catch (e) { if (e instanceof Preempt) throw e; } }
    const short = Math.min(w || 1080, hh || 1080), need = job.need.filter(x => x < short).sort((a, b) => a - b);
    for (let i = 0; i < need.length; i++) {
      const h = need[i], out = TMP + '/out_' + job.id + '_' + h + '.mp4';
      try { await encode(src, out, h, w, hh); } catch (e) { try { fs.unlinkSync(out); } catch (x) {} throw e; }
      const up = await upload(out, job.name.replace(/\.[^.]+$/, '') + ' (' + h + 'p).mp4', folder, job.id);
      await api('pxReport', { id: job.id, pid: up.id, h, size: up.size, last: i === need.length - 1 });
      fs.unlinkSync(out); log('  ✓ ' + h + 'p xong', Math.round(up.size / 1048576) + ' MB');
      if (CTX.pre) throw new Preempt();
    }
    if (!need.length) await api('pxReport', { id: job.id, fail: 'video nhỏ hơn 480p, không cần bản nhẹ' });
  } finally { try { fs.unlinkSync(src); } catch (e) {} }
}
const rlog = (m, lvl) => api('ghLog', { m, lvl }).catch(() => {});
const runP = (cmd, args, env) => new Promise((ok, no) => { const p = spawn(cmd, args, { stdio: 'inherit', env: Object.assign({}, process.env, env || {}) }); p.on('close', c => c === 0 ? ok() : no(new Error(cmd + ' thoát mã ' + c))); p.on('error', no); });
let toolsP = null, SUB = null;
function subTools() {
  if (process.env.NO_SUB) return Promise.resolve(false);
  return toolsP = toolsP || (async () => {
    try {
      if (!fs.existsSync(SV + '/bin/python')) { await runP('python3', ['-m', 'venv', SV]); try { await runP(SV + '/bin/pip', ['install', '-q', '--prefer-binary', 'faster-whisper', 'av<14', 'huggingface_hub', 'llama-cpp-python', '--extra-index-url', 'https://abetlen.github.io/llama-cpp-python/whl/cpu']); } catch (e) { await rlog('Phụ đề: cài Qwen lỗi (' + e.message + ') → chỉ chép lời, không dịch', 'err'); await runP(SV + '/bin/pip', ['install', '-q', '--prefer-binary', 'faster-whisper', 'av<14', 'huggingface_hub']); } }
      return true;
    } catch (e) { log('Cài công cụ phụ đề lỗi:', e.message); await rlog('Phụ đề: cài công cụ lỗi ' + e.message, 'err'); return false; }
  })();
}
function subProc() {
  if (SUB && !SUB.dead) return SUB;
  const p = spawn(SV + '/bin/python', ['subtitle.py'], { stdio: ['pipe', 'pipe', 'inherit'], env: Object.assign({}, process.env, { SUB_DAEMON: '1' }) });
  SUB = { p, dead: false, wait: null, buf: '' };
  p.stdout.on('data', d => { SUB.buf += d; let k; while ((k = SUB.buf.indexOf('\n')) >= 0) { const line = SUB.buf.slice(0, k).trim(); SUB.buf = SUB.buf.slice(k + 1); if (/^(DONE|FAIL) /.test(line) && SUB.wait) { const w = SUB.wait; SUB.wait = null; w(line); } else if (line) console.log(line); } });
  p.on('close', () => { SUB.dead = true; if (SUB.wait) { const w = SUB.wait; SUB.wait = null; w('DEAD'); } });
  return SUB;
}
async function sub(job) {
  if (!await subTools()) return;
  if (CTX.pre) throw new Preempt();
  log('  ▶ phụ đề'); const sp = subProc(), r = await new Promise(ok => { sp.wait = ok; CTX.subKill = () => { try { sp.p.kill('SIGKILL'); } catch (e) {} }; sp.p.stdin.write(job.id + '\t' + job.name.replace(/[\t\n]/g, ' ') + '\n'); });
  CTX.subKill = null;
  if (CTX.pre) throw new Preempt();
  if (r === 'DEAD') throw new Error('trình phụ đề dừng bất ngờ');
  log('  ' + (r.startsWith('DONE') ? '✓ phụ đề xong' : '✗ phụ đề lỗi'));
}
async function pipeline(job, folder) {
  CTX = { pre: false, kids: new Set(), ac: new AbortController(), subKill: null };
  const ctx = CTX, watch = setInterval(async () => { if (ctx.pre) return; try { const t = await api('nextJob', { peek: 1, skip: SKIP.slice(-50) }); if (t.job && t.job.id !== job.id && t.job.at > job.at) { ctx.pre = true; log('  ⏸ có file mới hơn → tạm dừng file này, làm file mới trước'); ctx.ac.abort(); ctx.kids.forEach(k => { try { k.kill('SIGKILL'); } catch (e) {} }); if (ctx.subKill) ctx.subKill(); } } catch (e) {} }, Number(process.env.WATCH_MS) || 30e3);
  try {
    if (job.need.length) await px(job, folder);
    if (job.sub) await sub(job);
    return 'ok';
  } catch (e) {
    if (e instanceof Preempt || ctx.pre) return 'pre';
    throw e;
  } finally { clearInterval(watch); CTX = null; }
}
async function main() {
  if (!API || !S) throw new Error('Thiếu MICC_API hoặc MICC_SECRET');
  await rlog('Bắt đầu lượt chạy (' + (process.env.GITHUB_EVENT_NAME || '?') + ')');
  subTools(); let done = 0, pre = 0; const fails = {};
  while (Date.now() < DEADLINE - 12 * 60e3) {
    const j = await api('nextJob', { skip: SKIP.slice(-50) });
    if (!j.job) { log('Hết việc ✓ (đã làm xong ' + done + ' video)'); break; }
    const job = j.job, fk = job.id + (job.need.length ? 'px' : 'sub'); 
    log('▶', job.name, '· còn', j.left, 'video chờ');
    try { const r = await pipeline(job, j.folder); if (r === 'pre') { pre++; await rlog('⏸ Tạm dừng “' + job.name + '” để làm file mới hơn'); } else { done++; SKIP.push(job.id); await rlog('✓ Xong hết: ' + job.name); } }
    catch (e) { fails[fk] = (fails[fk] || 0) + 1; const dead = DEAD.test(e.message) ? 1 : 0; if (dead || fails[fk] >= 2) SKIP.push(job.id); log('  ✗ lỗi:', e.message); try { if (job.need.length) await api('pxReport', { id: job.id, fail: e.message.slice(0, 300), dead }); if (job.sub && (dead || !job.need.length)) await api('subSave', { id: job.id, fail: e.message.slice(0, 200), dead }); } catch (x) {} }
  }
  if (SUB && !SUB.dead) try { SUB.p.stdin.end(); } catch (e) {}
  if (Date.now() >= DEADLINE - 12 * 60e3) log('Gần hết giờ chạy, lượt sau làm tiếp. Đã xong', done, 'video');
}
main().catch(e => { console.error(e); process.exit(1); });
