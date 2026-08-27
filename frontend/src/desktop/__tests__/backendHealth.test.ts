import { describe, expect, it, vi } from "vitest";
import { waitForBackendHealth } from "../backendHealth";

describe("backendHealth", () => {
  it("passes when /health responds", async () => {
    const fetchImpl = vi.fn(async () => ({ ok: true, status: 200 }) as Response);
    const result = await waitForBackendHealth("http://127.0.0.1:8000", { attempts: 1, fetchImpl });

    expect(result.ok).toBe(true);
    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/health");
  });

  it("reports failure after retries", async () => {
    const fetchImpl = vi.fn(async () => ({ ok: false, status: 503 }) as Response);
    const result = await waitForBackendHealth("http://127.0.0.1:8000", { attempts: 2, intervalMs: 1, fetchImpl });

    expect(result.ok).toBe(false);
    expect(result.error).toBe("HTTP 503");
  });

  it("re-resolves the backend URL between retries", async () => {
    let port = 8000;
    const resolveBaseUrl = vi.fn(() => `http://127.0.0.1:${port}`);
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.includes(":8000")) {
        port = 8011;
        throw new Error("not ready");
      }
      return { ok: true, status: 200 } as Response;
    });

    const result = await waitForBackendHealth(resolveBaseUrl, { attempts: 2, intervalMs: 1, fetchImpl });

    expect(result.ok).toBe(true);
    expect(result.baseUrl).toBe("http://127.0.0.1:8011");
    expect(fetchImpl).toHaveBeenLastCalledWith("http://127.0.0.1:8011/health");
  });
});
