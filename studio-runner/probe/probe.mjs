// Thử máy ảo GitHub cho MICC Studio: mã OIDC, mạng tới các nguồn miễn phí, cấu hình máy. Chỉ in thông tin trung tính.
import { execSync } from "node:child_process";
const sh = (c) => { try { return execSync(c, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: 120000 }).trim(); } catch (e) { return "ERR " + String(e.stderr || e.message).trim().split("\n").slice(-1)[0]; } };
const head = async (u, opt = {}) => { const t = Date.now(); try { const r = await fetch(u, { redirect: "follow", headers: { "user-agent": "micc-studio-runner/1.0 (probe)" }, signal: AbortSignal.timeout(15000), ...opt }); return `${r.status} ${Date.now() - t}ms`; } catch (e) { return "ERR " + (e.cause?.code || e.name); } };

console.log("== máy:", sh("nproc"), "CPU ·", sh("free -g | sed -n 2p | awk '{print $2\"GB RAM\"}'"), "·", sh("df -h / | tail -1 | awk '{print $4\" trống\"}'"), "· slot", process.env.RUNNER_NAME ? "ok" : "?");
console.log("== sẵn có:", "node", process.version, "| python", sh("python3 --version"), "| ffmpeg", sh("ffmpeg -version | head -1 | cut -c1-30"), "| chrome", sh("google-chrome --version"), "| sudo", sh("sudo -n true && echo ok"));
console.log("== tạo người dùng không quyền:", sh("sudo useradd -m studiotest && sudo -u studiotest sh -c 'id -un; sudo -n true 2>&1 | head -1'").replace(/\n/g, " | "));

try {
  const u = process.env.ACTIONS_ID_TOKEN_REQUEST_URL, tk = process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN;
  const r = await fetch(u + "&audience=miccstudio", { headers: { authorization: "Bearer " + tk } });
  const j = await r.json(), c = JSON.parse(Buffer.from(j.value.split(".")[1], "base64url").toString());
  const hd = JSON.parse(Buffer.from(j.value.split(".")[0], "base64url").toString());
  console.log("== OIDC ok:", JSON.stringify({ alg: hd.alg, iss: c.iss, aud: c.aud, repository: c.repository, ref: c.ref, event_name: c.event_name, workflow_ref: c.workflow_ref, job_workflow_ref: c.job_workflow_ref, runner_environment: c.runner_environment, ttl_s: c.exp - c.iat }));
  await new Promise((r) => setTimeout(r, 2000));
  const r2 = await fetch(u + "&audience=miccstudio", { headers: { authorization: "Bearer " + tk } });
  console.log("== OIDC xin lại lần 2:", r2.status);
} catch (e) { console.log("== OIDC lỗi:", e.message); }

const hosts = {
  studio: "https://miccstudio.pages.dev/dang-nhap",
  anthropic: "https://api.anthropic.com/v1/models",
  npm: "https://registry.npmjs.org/remotion",
  huggingface: "https://huggingface.co/Systran/faster-whisper-small/resolve/main/config.json",
  openfreemap_style: "https://tiles.openfreemap.org/styles/liberty",
  openfreemap_tiles: "https://tiles.openfreemap.org/planet",
  esri_imagery: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/12/1802/3254",
  aws_terrain: "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/10/451/813.png",
  nominatim: "https://nominatim.openstreetmap.org/search?q=Ha+Noi&format=json&limit=1",
  photon: "https://photon.komoot.io/api/?q=Ha%20Noi&limit=1",
  osrm: "https://router.project-osrm.org/route/v1/driving/105.85,21.03;105.80,21.00?overview=false",
  overpass: "https://overpass-api.de/api/status",
  openverse: "https://api.openverse.org/v1/images/?q=hanoi&page_size=1",
  wikimedia: "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=hanoi&srlimit=1",
  vnexpress: "https://vnexpress.net/",
  chinhphu: "https://chinhphu.vn/",
  gdrive_api: "https://www.googleapis.com/drive/v3/about",
};
for (const [k, u] of Object.entries(hosts)) console.log("   mạng", k.padEnd(18), await head(u));
console.log("== giờ cài Claude Code:", (() => { const t = Date.now(); const o = sh("npm i -g @anthropic-ai/claude-code >/dev/null 2>&1 && claude --version"); return o + " · " + Math.round((Date.now() - t) / 1000) + "s"; })());
console.log("== slot ma trận:", process.env.GITHUB_JOB, process.env.GITHUB_RUN_ATTEMPT, new Date().toISOString());
