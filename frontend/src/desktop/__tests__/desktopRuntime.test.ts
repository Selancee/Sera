import { describe, expect, it, beforeEach, vi } from "vitest";

describe("desktopRuntime", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
    window.seraDesktop = undefined;
  });

  it("detects desktop packaged runtime", async () => {
    window.seraDesktop = { packaged: true, backend: { port: 8012 } };
    const runtime = await import("../desktopRuntime");

    expect(runtime.isDesktopRuntime()).toBe(true);
    expect(runtime.resolveBackendBaseUrl()).toBe("http://127.0.0.1:8012");
  });

  it("re-reads the desktop backend port file through the bridge", async () => {
    window.seraDesktop = {
      packaged: true,
      backend: { port: 8000 },
      readBackend: vi.fn(() => ({ port: 8017 }))
    };
    const runtime = await import("../desktopRuntime");

    expect(runtime.resolveBackendBaseUrl()).toBe("http://127.0.0.1:8017");
    expect(window.seraDesktop.readBackend).toHaveBeenCalled();
  });

  it("falls back to developer backend URL", async () => {
    const runtime = await import("../desktopRuntime");

    expect(runtime.isDesktopRuntime()).toBe(false);
    expect(runtime.resolveBackendBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("receives notation sessions from the Electron preload bridge", async () => {
    const unsubscribe = vi.fn();
    const onOpenSession = vi.fn((callback) => {
      callback({ sequence: 2, session_id: "bridge_20260803_abcdef12" });
      return unsubscribe;
    });
    window.seraDesktop = {
      packaged: true,
      readPendingSession: () => ({ sequence: 1, session_id: "bridge_20260803_12345678" }),
      onOpenSession
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ backend_pid: 0, sequence: 2, pending: false, session_id: "" })
    } as Response);
    const runtime = await import("../desktopRuntime");
    const callback = vi.fn();

    expect(runtime.readPendingDesktopSession().session_id).toBe("bridge_20260803_12345678");
    const cleanup = runtime.subscribeDesktopOpenSession(callback);
    expect(callback).toHaveBeenCalledWith(expect.objectContaining({
      sequence: 2,
      session_id: "bridge_20260803_abcdef12"
    }));
    cleanup();
    expect(unsubscribe).toHaveBeenCalled();
  });

  it("recovers a notation session when the Electron renderer IPC notification is missed", async () => {
    const unsubscribe = vi.fn();
    window.seraDesktop = {
      packaged: true,
      backend: { base_url: "http://127.0.0.1:8000" },
      readPendingSession: () => ({
        backend_pid: 123,
        sequence: 3,
        session_id: "bridge_20260826_old12345"
      }),
      onOpenSession: vi.fn(() => unsubscribe)
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        backend_pid: 123,
        sequence: 4,
        pending: true,
        session_id: "bridge_20260826_new12345"
      })
    } as Response);
    const runtime = await import("../desktopRuntime");
    const callback = vi.fn();

    const cleanup = runtime.subscribeDesktopOpenSession(callback);
    await vi.waitFor(() => expect(callback).toHaveBeenLastCalledWith(expect.objectContaining({
      sequence: 4,
      session_id: "bridge_20260826_new12345"
    })));
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/integrations/desktop/pending-session?after_sequence=3&after_backend_pid=123"
    );
    cleanup();
    expect(unsubscribe).toHaveBeenCalled();
  });
});
