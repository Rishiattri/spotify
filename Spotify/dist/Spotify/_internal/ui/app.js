// System Activity Control — hybrid frontend
// Default: Spotify-style decoy view. Click "+" to reveal the real app.
// Communicates with Python via window.pywebview.api.*

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const state = {
  running: false,
  speed: "Medium",
  platform: "Windows",
  modifier: "ctrl",
  controllers: { mouse: false, keyboard: false, browser: false, vscode: false },
  logCount: 0,
  startedAt: null,
  view: "spotify",
};

const ENGINES = [
  { key: "mouse", title: "Mouse", desc: "Cursor movement, clicks, scroll" },
  { key: "keyboard", title: "Keyboard", desc: "Idle keys (Shift, Ctrl, modifiers)" },
  { key: "browser", title: "Browser", desc: "Tab switching across browsers" },
  { key: "vscode", title: "VS Code", desc: "Editor activity simulation" },
];

// ---------- Python bridge ----------
function api() { return (window.pywebview && window.pywebview.api) || null; }

async function call(fn, ...args) {
  const a = api();
  if (!a || typeof a[fn] !== "function") return null;
  try { return await a[fn](...args); }
  catch (e) { console.error(`api.${fn} failed`, e); return null; }
}

// ---------- Top-level view switch ----------
function showSpotify() {
  state.view = "spotify";
  $("#spotifyView").hidden = false;
  $("#appView").hidden = true;
}

function showApp() {
  state.view = "app";
  $("#spotifyView").hidden = true;
  $("#appView").hidden = false;
  refreshLogs(true);
  pollStatus();
}

$("#addBtn").addEventListener("click", showApp);
$("#exitAppViewBtn").addEventListener("click", showSpotify);
$("#homeBtn").addEventListener("click", showSpotify);

// Hidden shortcut: Ctrl+Shift+. toggles app view if you need a keyboard escape hatch
window.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === ">") {
    state.view === "spotify" ? showApp() : showSpotify();
  }
  if (e.key === "Escape" && state.view === "app") showSpotify();
});

// ---------- App-view tab nav ----------
function showTab(name) {
  $$(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  $$(".tab-panel").forEach(p => p.hidden = p.dataset.tab !== name);
  if (name === "controls") renderToggles();
  if (name === "logs") refreshLogs(true);
}
$$(".tab").forEach(t => t.addEventListener("click", () => showTab(t.dataset.tab)));

// ---------- Actions ----------
async function doStart() {
  if (state.running) return;
  const res = await call("start");
  if (res === null) { simulateLocalToggle(true); return; }
  Object.assign(state, normalize(res));
  state.startedAt = Date.now();
  renderAll();
}

async function doStop() {
  const res = await call("stop");
  if (res === null) { simulateLocalToggle(false); return; }
  Object.assign(state, normalize(res));
  state.startedAt = null;
  renderAll();
}

function simulateLocalToggle(running) {
  state.running = running;
  state.startedAt = running ? Date.now() : null;
  state.controllers = { mouse: running, keyboard: running, browser: running, vscode: running };
  renderAll();
}

function normalize(s) {
  return {
    running: !!s.running,
    speed: s.speed || state.speed,
    platform: s.platform || state.platform,
    modifier: s.modifier || state.modifier,
    controllers: s.controllers || state.controllers,
  };
}

// Bind play/stop only after DOM is parsed (script is at end of body so it's fine)
$("#playBtn").addEventListener("click", () => state.running ? doStop() : doStart());
$("#nowToggle").addEventListener("click", () => state.running ? doStop() : doStart());
$("#stopBtn").addEventListener("click", doStop);
$("#hideBtn2").addEventListener("click", () => call("hide_window"));
$("#permBtn").addEventListener("click", async () => {
  await call("check_permissions");
  showTab("logs");
});

// Big play button on the Spotify hero — purely visual, fakes a "playing" feel
$("#bigPlayBtn").addEventListener("click", () => {
  const icon = $("#bigPlayBtn svg");
  const isPlaying = icon.dataset.playing === "1";
  icon.dataset.playing = isPlaying ? "0" : "1";
  icon.innerHTML = isPlaying
    ? '<polygon points="7 4 21 12 7 20 7 4"/>'
    : '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>';
});

// Speed selectors
$$(".pill[data-speed]").forEach(p => p.addEventListener("click", () => setSpeed(p.dataset.speed)));
$$(".speed-card").forEach(c => c.addEventListener("click", () => setSpeed(c.dataset.speed)));

async function setSpeed(speed) {
  state.speed = speed;
  await call("set_speed", speed);
  renderSpeedUI();
}

// ---------- Renderers ----------
function renderAll() {
  renderRunningUI();
  renderSpeedUI();
  renderPlatform();
}

function renderRunningUI() {
  const hero = $("#hero");
  if (hero) hero.classList.toggle("active", state.running);
  if ($("#heroTitle")) $("#heroTitle").textContent = state.running ? "Active" : "Inactive";
  if ($("#heroSub")) $("#heroSub").textContent = state.running
    ? "All controllers running — keep your seat warm."
    : "Press play to start automation";
  if ($("#heroDot")) $("#heroDot").classList.toggle("live", state.running);

  const playIcon = $("#playIcon");
  const nowIcon = $("#nowToggleIcon");
  const playSvg = state.running
    ? '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>'
    : '<polygon points="6 4 20 12 6 20 6 4"/>';
  if (playIcon) playIcon.innerHTML = playSvg;
  if (nowIcon) nowIcon.innerHTML = playSvg;
  if ($("#playBtn")) $("#playBtn").classList.toggle("playing", state.running);

  if ($("#nowArt")) $("#nowArt").classList.toggle("active", state.running);
  renderControllers();
}

function renderControllers() {
  const active = Object.values(state.controllers).filter(Boolean).length;
  if ($("#statCtrl")) $("#statCtrl").textContent = `${active}/4`;
  if ($("#ctrlBar")) $("#ctrlBar").style.width = `${(active / 4) * 100}%`;
  if ($("#heroCtrlBadge")) $("#heroCtrlBadge").textContent = `${active}/4 controllers`;
  if ($("#ctrlSummary")) $("#ctrlSummary").textContent = active === 0 ? "All idle" : `${active} active`;

  $$(".ctrl-card").forEach(card => {
    const key = card.dataset.key;
    const on = !!state.controllers[key];
    card.classList.toggle("live", on);
    card.querySelector(".dot").classList.toggle("on", on);
    card.querySelector(".dot").classList.toggle("off", !on);
    card.querySelector(".ctrl-state").textContent = on ? "Active" : "Inactive";
  });
}

function renderSpeedUI() {
  if ($("#statSpeed")) $("#statSpeed").textContent = state.speed;
  if ($("#heroSpeedBadge")) $("#heroSpeedBadge").textContent = `${state.speed} speed`;
  $$(".pill[data-speed]").forEach(p => p.classList.toggle("active", p.dataset.speed === state.speed));
  $$(".speed-card").forEach(c => c.classList.toggle("active", c.dataset.speed === state.speed));
}

function renderPlatform() {
  if ($("#statPlatform")) $("#statPlatform").textContent = state.platform;
  if ($("#heroPlatform")) $("#heroPlatform").textContent = state.platform;
  if ($("#statPlatformSub")) $("#statPlatformSub").textContent = `Modifier: ${(state.modifier || "ctrl").toUpperCase()}`;
}

function renderToggles() {
  const list = $("#toggleList");
  if (!list) return;
  list.innerHTML = "";
  ENGINES.forEach(e => {
    const row = document.createElement("div");
    row.className = "toggle-row";
    const on = !!state.controllers[e.key];
    row.innerHTML = `
      <div class="info">
        <div class="ctrl-icon ${e.key}" style="width:36px;height:36px;border-radius:8px;margin:0;">
          ${iconFor(e.key)}
        </div>
        <div>
          <h4>${e.title}</h4>
          <p>${e.desc}</p>
        </div>
      </div>
      <div class="switch ${on ? "on" : ""}" data-key="${e.key}"></div>
    `;
    list.appendChild(row);
  });
  $$(".switch[data-key]").forEach(sw => sw.addEventListener("click", async () => {
    const key = sw.dataset.key;
    const newVal = !sw.classList.contains("on");
    sw.classList.toggle("on", newVal);
    state.controllers[key] = newVal;
    await call("toggle_controller", key, newVal);
    renderControllers();
  }));
}

function iconFor(k) {
  const m = {
    mouse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="2" width="12" height="20" rx="6"/><line x1="12" y1="6" x2="12" y2="10"/></svg>',
    keyboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/></svg>',
    browser: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    vscode: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
  };
  return m[k] || "";
}

// ---------- Logs ----------
async function refreshLogs(force = false) {
  if (state.view !== "app") return;
  const lines = await call("get_recent_logs", 300);
  if (!lines) return;
  const feed = $("#logFeed");
  if (!feed) return;
  const wasNearBottom = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 60;
  feed.innerHTML = lines.map(formatLogLine).join("");
  state.logCount = lines.length;
  if ($("#logCount")) $("#logCount").textContent = `${state.logCount} entries`;
  if (force || wasNearBottom) feed.scrollTop = feed.scrollHeight;
}

function formatLogLine(line) {
  const m = line.match(/^\[(.*?)\]\s+\[(.*?)\]\s+(.*)$/);
  if (!m) return `<div class="line">${escapeHtml(line)}</div>`;
  const [, ts, cat, msg] = m;
  const cls = cat.toUpperCase().startsWith("ERROR") ? "error" :
              cat.toUpperCase() === "SYSTEM" ? "system" : "";
  return `<div class="line ${cls}"><span style="color:var(--text-3)">${ts}</span> <span class="cat">[${cat}]</span> ${escapeHtml(msg)}</div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

// ---------- Now-bar elapsed timer ----------
function tickElapsed() {
  if (state.view !== "app") return;
  if (state.running && state.startedAt) {
    const sec = Math.floor((Date.now() - state.startedAt) / 1000);
    const mm = String(Math.floor(sec / 60)).padStart(2, "0");
    const ss = String(sec % 60).padStart(2, "0");
    if ($("#elapsed")) $("#elapsed").textContent = `${mm}:${ss}`;
    if ($("#progressFill")) $("#progressFill").style.width = `${(sec % 60) * (100 / 60)}%`;
  }
}

// ---------- Poll status ----------
async function pollStatus() {
  const s = await call("get_status");
  if (!s) return;
  Object.assign(state, normalize(s));
  if (s.started_at && !state.startedAt) state.startedAt = s.started_at * 1000;
  if (!s.running) state.startedAt = null;
  renderAll();
}

// ---------- Volume slider ----------
let lastVolume = 65;
const volumeBar = $("#volumeBar");
const volumeFill = $("#volumeFill");
const volumeThumb = volumeBar ? volumeBar.querySelector(".volume-thumb") : null;
const volIcon = $("#volIcon");
const volIconSvg = $("#volIconSvg");

function setVolume(pct, remember = true) {
  pct = Math.max(0, Math.min(100, pct));
  if (volumeFill) volumeFill.style.width = pct + "%";
  if (volumeThumb) volumeThumb.style.left = pct + "%";
  if (remember && pct > 0) lastVolume = pct;
  updateVolumeIcon(pct);
}

function updateVolumeIcon(pct) {
  if (!volIconSvg) return;
  let waves = "";
  if (pct === 0) {
    waves = '<path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="22" y1="9" x2="16" y2="15" stroke="currentColor" stroke-width="2"/><line x1="16" y1="9" x2="22" y2="15" stroke="currentColor" stroke-width="2"/>';
  } else if (pct < 40) {
    waves = '<path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="currentColor" stroke-width="2" fill="none"/>';
  } else {
    waves = '<path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07" stroke="currentColor" stroke-width="2" fill="none"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14" stroke="currentColor" stroke-width="2" fill="none"/>';
  }
  volIconSvg.innerHTML = waves;
}

if (volumeBar) {
  let dragging = false;
  const onMove = (e) => {
    const rect = volumeBar.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    setVolume((x / rect.width) * 100);
  };
  volumeBar.addEventListener("mousedown", (e) => { dragging = true; onMove(e); });
  window.addEventListener("mousemove", (e) => { if (dragging) onMove(e); });
  window.addEventListener("mouseup", () => { dragging = false; });
}

if (volIcon) {
  volIcon.addEventListener("click", () => {
    const cur = parseFloat(volumeFill.style.width) || 0;
    if (cur > 0) { lastVolume = cur; setVolume(0, false); }
    else { setVolume(lastVolume || 65); }
  });
}

// ---------- Progress bar (visual) ----------
const progressBar = $("#progressBar");
if (progressBar) {
  progressBar.addEventListener("click", (e) => {
    const rect = progressBar.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    $("#progressFill").style.width = Math.max(0, Math.min(100, pct)) + "%";
  });
}

// ---------- Bootstrap ----------
function bootstrap() {
  renderAll();
  pollStatus();
  setInterval(tickElapsed, 1000);
  setInterval(pollStatus, 1500);
  setInterval(() => { if (state.view === "app") refreshLogs(); }, 1500);
}

window.addEventListener("pywebviewready", bootstrap);
setTimeout(() => { if (!api()) bootstrap(); }, 600);
