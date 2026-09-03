const { app, BrowserWindow, ipcMain, shell } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

let backendProcess = null;
const ownedBackendPids = new Set();
let backendStopping = false;
let mainWindow = null;
let sessionPollTimer = null;
let latestDesktopSession = { backend_pid: 0, sequence: 0, session_id: "" };

function bringWindowToFront(win) {
  if (!win || win.isDestroyed()) return;
  if (win.isMinimized()) win.restore();
  app.focus();
  win.setFocusable(true);
  win.show();
  win.setAlwaysOnTop(true, "screen-saver");
  win.moveTop();
  win.focus();
  setTimeout(() => {
    if (!win.isDestroyed()) win.setAlwaysOnTop(false);
  }, 3000);
}

const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    bringWindowToFront(mainWindow);
  });
}

function backendExecutable() {
  return path.join(desktopRoot(), "backend", "SeraBackend.exe");
}

function sourceRoot() {
  return path.join(__dirname, "..");
}

function desktopRoot() {
  const parent = path.join(__dirname, "..");
  if (fs.existsSync(path.join(parent, "backend", "SeraBackend.exe"))) return parent;
  return app.isPackaged ? process.resourcesPath : path.join(parent, "dist_desktop");
}

function frontendIndexPath() {
  if (!app.isPackaged) {
    return path.join(sourceRoot(), "frontend", "dist", "index.html");
  }
  return path.join(desktopRoot(), "frontend", "dist", "index.html");
}

function runtimeDir() {
  return path.join(app.getPath("userData"), "runtime");
}

function portFilePath() {
  return path.join(runtimeDir(), "backend_port.json");
}

function readPublishedBackendRuntime() {
  const candidates = [
    portFilePath(),
    path.join(app.getPath("userData"), "backend_port.json")
  ];
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) {
        const runtime = {
          runtime_dir: runtimeDir(),
          ...JSON.parse(fs.readFileSync(candidate, "utf8"))
        };
        if (runtime.base_url && Number.isInteger(Number(runtime.port))) return runtime;
      }
    } catch {
      // Keep desktop startup fallback-safe if the runtime file is half-written.
    }
  }
  return null;
}

function readBackendPort() {
  return readPublishedBackendRuntime() || {
    runtime_dir: runtimeDir(),
    host: "127.0.0.1",
    port: 8000,
    base_url: "http://127.0.0.1:8000"
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function backendStartupTimeoutMs() {
  const configured = Number(process.env.SERA_BACKEND_STARTUP_TIMEOUT_MS || 0);
  if (Number.isFinite(configured) && configured >= 1000) return configured;
  return app.isPackaged ? 90000 : 45000;
}

async function backendHealth(runtime, timeoutMs = 2000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${runtime.base_url.replace(/\/$/, "")}/health`, {
      signal: controller.signal
    });
    if (!response.ok) return { ok: false, error: `HTTP ${response.status}` };
    const payload = await response.json();
    return payload.status === "ok"
      ? { ok: true }
      : { ok: false, error: `unexpected health status: ${String(payload.status || "missing")}` };
  } catch (error) {
    return { ok: false, error: String(error) };
  } finally {
    clearTimeout(timer);
  }
}

async function waitForBackendReady(timeoutMs = backendStartupTimeoutMs()) {
  const started = Date.now();
  let lastError = "runtime port has not been published";
  while (Date.now() - started < timeoutMs) {
    const runtime = readPublishedBackendRuntime();
    if (runtime) {
      const health = await backendHealth(runtime);
      if (health.ok) return runtime;
      lastError = health.error;
    } else if (backendProcess === null) {
      throw new Error("Sera backend exited before publishing its runtime port.");
    }
    await sleep(250);
  }
  throw new Error(
    `Sera backend was not healthy within ${Math.round(timeoutMs / 1000)} seconds. Last state: ${lastError}`
  );
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function startupPageHtml(error = "") {
  const failed = Boolean(error);
  const heading = failed ? "Sera 本地引擎启动失败" : "正在启动 Sera 本地引擎";
  const detail = failed
    ? escapeHtml(error)
    : "正在解压并加载乐谱编辑服务。首次启动通常需要 15–60 秒，请勿重复打开应用。";
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Sera</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f4f2eb;color:#17211e;font-family:"Segoe UI","Microsoft YaHei",sans-serif}.card{width:min(560px,calc(100vw - 48px));padding:42px;border:1px solid #d8d4c8;border-radius:22px;background:#fff;box-shadow:0 18px 60px rgba(24,35,31,.1)}.brand{display:flex;align-items:center;gap:14px;margin-bottom:28px}.mark{display:grid;place-items:center;width:48px;height:48px;border-radius:14px;background:#17211e;color:#fff;font-size:24px;font-weight:700}h1{margin:0;font-size:25px}p{margin:12px 0 0;color:#58635f;line-height:1.7}.bar{height:6px;margin-top:28px;overflow:hidden;border-radius:999px;background:#e6e3da}.bar::after{content:"";display:block;width:42%;height:100%;border-radius:inherit;background:#16866f;animation:loading 1.35s ease-in-out infinite}.error{padding:14px 16px;border-radius:12px;background:#fff1ed;color:#8b2f24;word-break:break-word}.hint{font-size:13px}@keyframes loading{0%{transform:translateX(-110%)}100%{transform:translateX(340%)}}
</style></head><body><main class="card"><div class="brand"><div class="mark">S</div><div><h1>${heading}</h1><p>Sera · 智能乐谱编辑与协作层</p></div></div><p class="${failed ? "error" : ""}">${detail}</p>${failed ? '<p class="hint">请关闭应用后重试；若持续失败，请检查 8000 端口和打包日志。</p>' : '<div class="bar" aria-label="正在加载"></div><p class="hint">后端健康检查通过后，工作台会自动出现。</p>'}</main></body></html>`;
}

async function showStartupPage(win, error = "") {
  if (!win || win.isDestroyed()) return;
  const url = `data:text/html;charset=utf-8,${encodeURIComponent(startupPageHtml(error))}`;
  await win.loadURL(url);
}

async function probeExistingDesktopBackend(timeoutMs = 1500) {
  const runtime = readBackendPort();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${runtime.base_url}/integrations/desktop/status`, {
      signal: controller.signal
    });
    if (!response.ok) return null;
    const status = await response.json();
    if (status.desktop_available !== true) return null;
    const pid = Number(status.backend_pid || runtime.pid || 0);
    if (!Number.isInteger(pid) || pid <= 0) return null;
    return { ...runtime, pid };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function publishAdoptedRuntime(runtime) {
  fs.mkdirSync(runtimeDir(), { recursive: true });
  fs.writeFileSync(
    portFilePath(),
    JSON.stringify(
      {
        host: runtime.host || "127.0.0.1",
        port: Number(runtime.port || 8000),
        base_url: runtime.base_url || "http://127.0.0.1:8000",
        pid: Number(runtime.pid)
      },
      null,
      2
    ),
    "utf8"
  );
}

function terminateProcessTree(pid) {
  const processId = Number(pid);
  if (!Number.isInteger(processId) || processId <= 0 || processId === process.pid) return;
  if (process.platform === "win32") {
    const taskkill = path.join(process.env.SystemRoot || "C:\\Windows", "System32", "taskkill.exe");
    const result = spawnSync(taskkill, ["/pid", String(processId), "/T", "/F"], {
      windowsHide: true,
      stdio: "ignore"
    });
    if (result.status === 0) return;
    try {
      process.kill(processId, "SIGKILL");
    } catch {
      // The backend may already have exited.
    }
    return;
  }
  try {
    process.kill(processId, "SIGTERM");
  } catch {
    // The backend may already have exited.
  }
}

function stopBackend() {
  if (backendStopping) return;
  backendStopping = true;
  for (const pid of ownedBackendPids) terminateProcessTree(pid);
  ownedBackendPids.clear();
  backendProcess = null;
  try {
    if (fs.existsSync(portFilePath())) fs.unlinkSync(portFilePath());
  } catch {
    // Runtime cleanup must not block application shutdown.
  }
  backendStopping = false;
}

ipcMain.on("sera:read-backend-sync", (event) => {
  event.returnValue = readBackendPort();
});

ipcMain.on("sera:read-pending-session-sync", (event) => {
  event.returnValue = latestDesktopSession;
});

ipcMain.handle("sera:open-local-review-file", async (_event, requestedPath) => {
  const reviewRoot = path.resolve(app.getPath("userData"), "research_reviews");
  const resolved = path.resolve(String(requestedPath || ""));
  const allowedExtensions = new Set([".musicxml", ".xml", ".json", ".csv"]);
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) {
    return { ok: false, error: "The prepared review file no longer exists." };
  }
  const realRoot = fs.realpathSync(reviewRoot);
  const realResolved = fs.realpathSync(resolved);
  const comparableRoot = process.platform === "win32" ? realRoot.toLowerCase() : realRoot;
  const comparableResolved = process.platform === "win32" ? realResolved.toLowerCase() : realResolved;
  const withinReviewRoot = comparableResolved.startsWith(`${comparableRoot}${path.sep}`);
  if (!withinReviewRoot || !allowedExtensions.has(path.extname(realResolved).toLowerCase())) {
    return { ok: false, error: "Sera refused to open a path outside the local review workspace." };
  }
  const error = await shell.openPath(realResolved);
  return error ? { ok: false, error } : { ok: true };
});

function startBackend() {
  const exe = backendExecutable();
  const runtime = runtimeDir();
  fs.mkdirSync(runtime, { recursive: true });
  try {
    if (fs.existsSync(portFilePath())) fs.unlinkSync(portFilePath());
  } catch {
    // Stale runtime files must not prevent desktop startup.
  }
  const backendEnv = {
    ...process.env,
    SERA_RUNTIME_DIR: runtime,
    SERA_BACKEND_PORT: process.env.SERA_BACKEND_PORT || "8000",
    SERA_DESKTOP_MODE: "1",
    SERA_DESKTOP_STRICT_PORT: "1"
  };
  let command = exe;
  let args = [];
  let cwd = desktopRoot();
  if (!app.isPackaged) {
    const python = path.join(sourceRoot(), ".venv", "Scripts", "python.exe");
    const launcher = path.join(sourceRoot(), "packaging", "backend", "run_backend_packaged.py");
    if (!fs.existsSync(python) || !fs.existsSync(launcher)) {
      return { ok: false, error: `Development backend launcher not found: ${launcher}` };
    }
    command = python;
    args = [launcher];
    cwd = sourceRoot();
  } else if (!fs.existsSync(exe)) {
    return { ok: false, error: `Backend executable not found: ${exe}` };
  }
  backendProcess = spawn(command, args, {
    cwd,
    env: backendEnv,
    windowsHide: true,
    stdio: "ignore"
  });
  if (backendProcess.pid) ownedBackendPids.add(backendProcess.pid);
  backendProcess.on("exit", () => {
    backendProcess = null;
  });
  return { ok: true };
}

async function ensureBackend() {
  const existing = await probeExistingDesktopBackend();
  if (existing) {
    ownedBackendPids.add(existing.pid);
    publishAdoptedRuntime(existing);
    return { ok: true, runtime: existing, adopted: true };
  }
  const startup = startBackend();
  if (!startup.ok) return startup;
  const runtime = await waitForBackendReady();
  const runtimePid = Number(runtime.pid || 0);
  if (Number.isInteger(runtimePid) && runtimePid > 0) ownedBackendPids.add(runtimePid);
  return { ok: true, runtime, adopted: false };
}

async function pollDesktopSession(win) {
  if (!win || win.isDestroyed()) return;
  const runtime = readBackendPort();
  const baseUrl = runtime.base_url || "http://127.0.0.1:8000";
  try {
    const response = await fetch(
      `${baseUrl}/integrations/desktop/pending-session?after_sequence=${latestDesktopSession.sequence || 0}` +
      `&after_backend_pid=${latestDesktopSession.backend_pid || 0}`
    );
    if (!response.ok) return;
    const payload = await response.json();
    const backendPid = Number(payload.backend_pid || 0);
    const backendChanged =
      latestDesktopSession.backend_pid > 0 &&
      backendPid > 0 &&
      latestDesktopSession.backend_pid !== backendPid;
    if (backendChanged) {
      latestDesktopSession = { backend_pid: backendPid, sequence: 0, session_id: "" };
    } else if (backendPid > 0) {
      latestDesktopSession.backend_pid = backendPid;
    }
    if (!payload.pending || !payload.session_id) return;
    latestDesktopSession = {
      backend_pid: backendPid,
      sequence: Number(payload.sequence || 0),
      session_id: String(payload.session_id)
    };
    bringWindowToFront(win);
    win.webContents.send("sera:open-session", latestDesktopSession);
  } catch {
    // Backend readiness and transient shutdown races are retried by the timer.
  }
}

function startSessionPolling(win) {
  if (sessionPollTimer) clearInterval(sessionPollTimer);
  sessionPollTimer = setInterval(() => pollDesktopSession(win), 750);
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    title: "Sera",
    icon: path.join(__dirname, "icon.png"),
    show: false,
    backgroundColor: "#f4f2eb",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  mainWindow = win;
  win.on("closed", () => {
    if (sessionPollTimer) clearInterval(sessionPollTimer);
    sessionPollTimer = null;
    mainWindow = null;
  });
  await showStartupPage(win);
  if (win.isDestroyed()) return;
  win.show();
  try {
    const startup = await ensureBackend();
    if (!startup.ok) throw new Error(startup.error);
  } catch (error) {
    await showStartupPage(win, String(error));
    return;
  }
  const indexPath = frontendIndexPath();
  if (!fs.existsSync(indexPath)) {
    await showStartupPage(win, `Sera frontend build not found: ${indexPath}`);
    return;
  }
  await win.loadFile(indexPath, { query: { desktop: "1" } });
  startSessionPolling(win);
}

if (singleInstanceLock) app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (sessionPollTimer) clearInterval(sessionPollTimer);
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", stopBackend);
