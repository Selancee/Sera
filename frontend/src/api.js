const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function generateScore(prompt) {
  return request("/generate", {
    method: "POST",
    body: JSON.stringify({ prompt })
  });
}

export function reviseScore(runId, feedback) {
  return request("/revise", {
    method: "POST",
    body: JSON.stringify({ run_id: runId, feedback })
  });
}

export function evaluateRun(runId) {
  return request("/evaluate", {
    method: "POST",
    body: JSON.stringify({ run_id: runId })
  });
}

export function submitRating(runId, rating) {
  return request("/rate", {
    method: "POST",
    body: JSON.stringify({ run_id: runId, ...rating })
  });
}

export function getExportUrl(runId, format) {
  return `${API_BASE}/export/${runId}/${format}`;
}

export function listExperiments() {
  return request("/experiments?limit=20");
}
