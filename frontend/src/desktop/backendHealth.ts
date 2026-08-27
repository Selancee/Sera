export type BackendHealthResult = {
  ok: boolean;
  baseUrl: string;
  attempts: number;
  error?: string;
};

export async function waitForBackendHealth(
  baseUrl: string | (() => string),
  options: { attempts?: number; intervalMs?: number; fetchImpl?: typeof fetch } = {}
): Promise<BackendHealthResult> {
  const attempts = options.attempts ?? 120;
  const intervalMs = options.intervalMs ?? 250;
  const fetchImpl = options.fetchImpl ?? fetch;
  let lastError = "";
  let currentBaseUrl = typeof baseUrl === "function" ? baseUrl() : baseUrl;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    currentBaseUrl = typeof baseUrl === "function" ? baseUrl() : baseUrl;
    try {
      const response = await fetchImpl(`${currentBaseUrl.replace(/\/$/, "")}/health`);
      if (response.ok) return { ok: true, baseUrl: currentBaseUrl, attempts: attempt };
      lastError = `HTTP ${response.status}`;
    } catch (error: any) {
      lastError = error?.message || String(error);
    }
    if (attempt < attempts) await delay(intervalMs);
  }
  return { ok: false, baseUrl: currentBaseUrl, attempts, error: lastError || "Backend did not respond." };
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
