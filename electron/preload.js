const { contextBridge, ipcRenderer } = require("electron");

function readBackendPort() {
  try {
    return ipcRenderer.sendSync("sera:read-backend-sync");
  } catch {
    return { base_url: "http://127.0.0.1:8000" };
  }
}

const initialBackend = readBackendPort();

function readPendingSession() {
  try {
    return ipcRenderer.sendSync("sera:read-pending-session-sync");
  } catch {
    return { sequence: 0, session_id: "" };
  }
}

contextBridge.exposeInMainWorld("seraDesktop", {
  packaged: true,
  runtimeDir: initialBackend.runtime_dir || "",
  backend: initialBackend,
  readBackend: readBackendPort,
  readPendingSession,
  openLocalFile(path) {
    return ipcRenderer.invoke("sera:open-local-review-file", path);
  },
  onOpenSession(callback) {
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on("sera:open-session", handler);
    return () => ipcRenderer.removeListener("sera:open-session", handler);
  }
});
