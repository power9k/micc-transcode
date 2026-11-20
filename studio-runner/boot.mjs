// Mồi máy dựng MICC Studio (công khai – KHÔNG chứa gì riêng tư). Chỉ dùng Node có sẵn, không cần npm install.
//   node boot.mjs prepare   xin mã OIDC → hello → tải pack → kiểm sha256 → giải nén /srv/studio/pack → ghi khóa bộ đệm
//   node boot.mjs serve     cài phụ thuộc (bỏ qua nếu bộ đệm còn đúng) → tạo người dùng studio → chạy pack/run.mjs --serve tới phút ~330
// Nhật ký Actions là công khai: chỉ in dòng trung tính, che mọi mã bằng ::add-mask::.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync, spawn } from 'node:child_process';

const URL_ = (process.env.STUDIO_URL || 'https://miccstudio.pages.dev').replace(/\/+$/, '');
const ROOT = process.env.STUDIO_BOOT_ROOT || '/srv/studio';   // biến chỉ để chạy thử
const PACK = ROOT + '/pack', MOD = ROOT + '/kit_modules', CACHE = ROOT + '/cache';
const T0_FILE = ROOT + '/.t0';
const log = (m) => console.log('[boot] ' + m);
const sh = (cmd, args, o = {}) => { const r = spawnSync(cmd, args, { stdio: o.quiet ? ['ignore', 'ignore', 'pipe'] : 'inherit', env: o.env || process.env, cwd: o.cwd, timeout: o.timeout || 1800e3 }); return r.status === 0; };
const sudo = (...a) => sh('sudo', ['-n', ...a], { quiet: true });

async function oidc() {
  const u = process.env.ACTIONS_ID_TOKEN_REQUEST_URL, t = process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN;
  if (!u || !t) throw new Error('no oidc (permissions id-token: write?)');
  const r = await fetch(u + '&audience=miccstudio', { headers: { authorization: 'Bearer ' + t } });
  const j = await r.json();
  if (!j.value) throw new Error('oidc ' + r.status);
  console.log('::add-mask::' + j.value);
  return j.value;
}
async function hello() {
  for (let n = 0; ; n++) {
    try {
      const r = await fetch(URL_ + '/api/runner/hello', { method: 'POST', headers: { authorization: 'Bearer ' + await oidc(), 'content-type': 'application/json' }, body: JSON.stringify({ name: 'boot', pack: '' }) });
      const j = await r.json().catch(() => ({}));
      if (r.ok && j.session) { console.log('::add-mask::' + j.session); return j; }
      log('hello http ' + r.status);
    } catch (e) { log('hello error ' + String(e.message).replace(/[^\w .:-]/g, '').slice(0, 80)); }
    if (n >= 8) throw new Error('hello failed');
    await new Promise((r) => setTimeout(r, 5000 * (n + 1)));
  }
}

// Tải pack (kiểm sha256 nếu máy chủ cho biết) rồi giải nén vào thư mục mới, đổi chỗ nguyên khối.
async function fetchPack() {
  const h = await hello();
  const want = h.pack || {};
  const r = await fetch(URL_ + '/api/runner/pack' + (want.ver ? '?ver=' + encodeURIComponent(want.ver) : ''), { headers: { authorization: 'Bearer ' + h.session } });
  if (!r.ok) throw new Error('pack http ' + r.status);
  const buf = Buffer.from(await r.arrayBuffer());
  const sha = crypto.createHash('sha256').update(buf).digest('hex');
  const expect = want.sha256 || r.headers.get('x-pack-sha256') || '';
  if (expect && expect !== sha) throw new Error('pack sha256 mismatch');
  const ver = want.ver || r.headers.get('x-pack-ver') || sha.slice(0, 12);
  log(`pack ${ver} ${(buf.length / 1048576).toFixed(1)} MB ${expect ? 'verified' : 'unverified'}`);
  const tgz = ROOT + '/pack.tgz', tmp = ROOT + '/pack.new';
  fs.writeFileSync(tgz, buf);
  fs.rmSync(tmp, { recursive: true, force: true }); fs.mkdirSync(tmp);
  if (!sh('tar', ['-xzf', tgz, '-C', tmp, '--no-same-owner'])) throw new Error('pack extract failed');
  fs.rmSync(PACK, { recursive: true, force: true }); fs.renameSync(tmp, PACK); fs.rmSync(tgz, { force: true });
  fs.chmodSync(ROOT, 0o755);
  sh('chmod', ['-R', 'a+rX', PACK]);
  fs.writeFileSync(ROOT + '/.packver', ver);
  return ver;
}
const depKey = () => crypto.createHash('sha256').update(fs.readFileSync(PACK + '/kit/package-lock.json')).update(fs.existsSync(PACK + '/py/requirements.txt') ? fs.readFileSync(PACK + '/py/requirements.txt') : '').digest('hex').slice(0, 24);

function deps(env) {
  const key = depKey();
  const mark = MOD + '/.key';
  if (!(fs.existsSync(mark) && fs.readFileSync(mark, 'utf8') === key && fs.existsSync(MOD + '/node_modules/remotion'))) {
    log('install kit modules');
    fs.mkdirSync(MOD, { recursive: true });
    for (const f of ['package.json', 'package-lock.json']) fs.copyFileSync(path.join(PACK, 'kit', f), path.join(MOD, f));
    if (!sh('npm', ['ci', '--no-audit', '--no-fund', '--loglevel=error'], { cwd: MOD, env, quiet: true })) throw new Error('npm ci failed');
    fs.writeFileSync(mark, key);
  } else log('kit modules from cache');
  // Trình duyệt của Remotion (nằm trong node_modules → theo bộ đệm).
  sh('npx', ['--no-install', 'remotion', 'browser', 'ensure'], { cwd: MOD, env, quiet: true }) || log('remotion browser ensure failed');
  if (fs.existsSync(PACK + '/py/requirements.txt')) sh('python3', ['-m', 'pip', 'install', '-q', '-r', PACK + '/py/requirements.txt'], { env, quiet: true }) || log('pip install failed');
  sh('npm', ['i', '-g', '--no-audit', '--no-fund', '--loglevel=error', '@anthropic-ai/claude-code', 'playwright'], { env, quiet: true }) || log('npm global install failed');
  sh('npx', ['--no-install', 'playwright', 'install', '--with-deps', 'chromium'], { env, quiet: true }) || log('playwright install failed');
  sh('chmod', ['-R', 'a+rX', MOD, CACHE + '/ms-playwright']);
}

function makeUser() {
  if (spawnSync('id', ['studio'], { stdio: 'ignore' }).status !== 0) sudo('useradd', '-m', '-s', '/bin/bash', 'studio') || log('useradd failed');
  // Người dùng studio không có sudo, không vào được thư mục của runner.
  sudo('chmod', '700', process.env.HOME || '/home/runner');
}

async function main() {
  const mode = process.argv[2];
  if (mode === 'prepare') {
    sudo('mkdir', '-p', ROOT); sudo('chown', `${process.getuid()}:${process.getgid()}`, ROOT);
    for (const d of [CACHE + '/whisper', CACHE + '/pip', CACHE + '/ms-playwright', MOD]) fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(T0_FILE, String(Date.now()));
    await fetchPack();
    if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, `key=${depKey()}\n`);
    return;
  }
  if (mode !== 'serve') throw new Error('usage: boot.mjs prepare|serve');
  const t0 = Number(fs.existsSync(T0_FILE) ? fs.readFileSync(T0_FILE, 'utf8') : 0) || Date.now();
  const stopAt = t0 + Number(process.env.STUDIO_RUN_MINUTES || 330) * 60e3;
  const globalRoot = spawnSync('npm', ['root', '-g'], { encoding: 'utf8' }).stdout.trim();
  const env = { ...process.env, PIP_CACHE_DIR: CACHE + '/pip', PLAYWRIGHT_BROWSERS_PATH: CACHE + '/ms-playwright', NODE_PATH: globalRoot, PIP_DISABLE_PIP_VERSION_CHECK: '1' };
  deps(env);
  makeUser();
  for (const d of [ROOT + '/jobs', ROOT + '/logs']) fs.mkdirSync(d, { recursive: true });
  fs.chmodSync(ROOT + '/jobs', 0o711); fs.chmodSync(ROOT + '/logs', 0o700);
  // Chạy pack; mã 75 = có pack mới → tải lại rồi chạy tiếp. Mọi lỗi khác: thoát 0 (lượt matrix sau sẽ nối tiếp).
  for (let round = 0; round < 50 && Date.now() < stopAt - 10 * 60e3; round++) {
    const ver = fs.readFileSync(ROOT + '/.packver', 'utf8');
    const code = await new Promise((res) => {
      const p = spawn(process.execPath, [PACK + '/run.mjs', '--serve'], { stdio: 'inherit',
        env: { ...env, STUDIO_URL: URL_, STUDIO_ROOT: ROOT, STUDIO_AGENT_USER: 'studio', STUDIO_KIT_MODULES: MOD + '/node_modules', STUDIO_WHISPER_DIR: CACHE + '/whisper',
          STUDIO_PACK_VER: ver, STUDIO_STOP_AT: String(stopAt), STUDIO_RUNNER_NAME: 'gh-' + (process.env.GITHUB_RUN_ID || '') + '-' + (process.env.GITHUB_RUN_ATTEMPT || '') } });
      p.on('exit', (c) => res(c ?? 1));
    });
    log('runner exit ' + code);
    if (code !== 75) { if (code === 0) break; await new Promise((r) => setTimeout(r, 15000)); continue; }
    try { await fetchPack(); deps(env); } catch (e) { log('pack update failed'); await new Promise((r) => setTimeout(r, 30000)); }
  }
  log('done');
}
main().catch((e) => { log('error ' + String(e.message).replace(/[^\w .:()-]/g, '').slice(0, 100)); process.exit(process.argv[2] === 'prepare' ? 1 : 0); });
