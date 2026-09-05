export type SeraDesktopBridge = {
  packaged?: boolean;
  runtimeDir?: string;
  backend?: {
    base_url?: string;
    port?: number;
    host?: string;
  };
  readBackend?: () => {
    base_url?: string;
    port?: number;
    host?: string;
  };
  readPendingSession?: () => DesktopSessionMessage;
  onOpenSession?: (callback: (payload: DesktopSessionMessage) => void) => () => void;
  openLocalFile?: (path: string) => Promise<{ ok: boolean; error?: string }>;
};

export type DesktopSessionMessage = {
  backend_pid?: number;
  sequence?: number;
  session_id?: string;
  pending?: boolean;
};

declare global {
  interface Window {
    seraDesktop?: SeraDesktopBridge;
  }
}

export function isDesktopRuntime() {
  return Boolean(window.seraDesktop?.packaged);
}

export function resolveBackendBaseUrl() {
  const viteUrl = import.meta.env.VITE_API_BASE_URL;
  if (viteUrl) return String(viteUrl).replace(/\/$/, "");
  const bridge = window.seraDesktop;
  const backend = bridge?.readBackend?.() || bridge?.backend;
  if (backend?.base_url) return backend.base_url.replace(/\/$/, "");
  if (backend?.port) return `http://${backend.host || "127.0.0.1"}:${backend.port}`;
  return "http://127.0.0.1:8000";
}

export function readPendingDesktopSession() {
  return window.seraDesktop?.readPendingSession?.() || { sequence: 0, session_id: "" };
}

export function subscribeDesktopOpenSession(callback: (payload: DesktopSessionMessage) => void) {
  const bridge = window.seraDesktop;
  let stopped = false;
  let pollInFlight = false;
  let cursor = 0;
  let backendPid = 0;
  let deliveredSequence = -1;
  let deliveredSessionId = "";

  const deliver = (payload: DesktopSessionMessage) => {
    const sessionId = String(payload.session_id || "");
    if (!sessionId) return;
    const sequence = Number(payload.sequence || 0);
    const nextBackendPid = Number(payload.backend_pid || backendPid || 0);
    if (
      sessionId === deliveredSessionId
      && sequence === deliveredSequence
      && nextBackendPid === backendPid
    ) return;
    backendPid = nextBackendPid;
    cursor = sequence;
    deliveredSequence = sequence;
    deliveredSessionId = sessionId;
    callback({ ...payload, backend_pid: backendPid, sequence, session_id: sessionId });
  };

  // An IPC notification can arrive before React subscribes. Re-deliver the
  // main-process snapshot first, then independently poll the local backend so
  // a dropped renderer notification cannot leave Sera bound to an old score.
  const initial = readPendingDesktopSession();
  backendPid = Number(initial.backend_pid || 0);
  cursor = Number(initial.sequence || 0);
  deliver(initial);

  const unsubscribeIpc = bridge?.onOpenSession?.(deliver) || (() => {});
  const poll = async () => {
    if (stopped || pollInFlight || !bridge?.packaged) return;
    pollInFlight = true;
    try {
      const response = await fetch(
        `${resolveBackendBaseUrl()}/integrations/desktop/pending-session`
        + `?after_sequence=${encodeURIComponent(String(cursor))}`
        + `&after_backend_pid=${encodeURIComponent(String(backendPid))}`
      );
      if (!response.ok) return;
      const payload = await response.json() as DesktopSessionMessage;
      const nextBackendPid = Number(payload.backend_pid || 0);
      if (nextBackendPid > 0 && nextBackendPid !== backendPid) {
        backendPid = nextBackendPid;
        cursor = 0;
      }
      if (payload.pending !== false) deliver(payload);
    } catch {
      // The timer retries transient backend startup and shutdown races.
    } finally {
      pollInFlight = false;
    }
  };

  void poll();
  const timer = bridge?.packaged ? window.setInterval(poll, 750) : null;
  return () => {
    stopped = true;
    unsubscribeIpc();
    if (timer !== null) window.clearInterval(timer);
  };
}

export async function openDesktopLocalFile(path: string) {
  if (!window.seraDesktop?.openLocalFile) {
    return { ok: false, error: "Local host inspection files can only be opened directly in Sera Desktop." };
  }
  return window.seraDesktop.openLocalFile(path);
}
