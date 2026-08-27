import { resolveBackendBaseUrl } from "./desktop/desktopRuntime";

function apiBase() {
  return resolveBackendBaseUrl();
}

async function request(path, options = {}) {
  const { timeoutMs = 0, ...fetchOptions } = options;
  const controller = timeoutMs > 0 ? new AbortController() : null;
  const timeoutId = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null;
  try {
    const response = await fetch(`${apiBase()}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(fetchOptions.headers || {})
      },
      ...fetchOptions,
      signal: controller?.signal || fetchOptions.signal
    });
    if (!response.ok) {
      const detail = await response.text();
      let message = detail;
      try {
        const payload = JSON.parse(detail);
        message = typeof payload.detail === "string" ? payload.detail : detail;
      } catch {
        // Keep non-JSON backend errors readable.
      }
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response.json();
  } catch (error) {
    if (controller?.signal.aborted) {
      throw new Error(`Sera 后端在 ${Math.round(timeoutMs / 1000)} 秒内没有返回，请重试或检查模型 API。`);
    }
    throw error;
  } finally {
    if (timeoutId !== null) window.clearTimeout(timeoutId);
  }
}

export function generateScore(promptOrRequest, options = {}) {
  const body = typeof promptOrRequest === "string"
    ? { raw_prompt: promptOrRequest, prompt: promptOrRequest, ...options }
    : { ...(promptOrRequest || {}) };
  return request("/generate", {
    method: "POST",
    body: JSON.stringify(body)
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

export function getSymbolicModelStatus() {
  return request("/model/status");
}

export function getSymbolicModelRegistry() {
  return request("/model/registry");
}

export function selectSymbolicModel(modelName, persist = true) {
  return request("/model/select", {
    method: "POST",
    body: JSON.stringify({ model_name: modelName, persist })
  });
}

export function generateSymbolicModelSample(prompt, maxTokens = 96) {
  return request("/model/sample", {
    method: "POST",
    body: JSON.stringify({ prompt, max_tokens: maxTokens })
  });
}

export function submitRating(runId, rating) {
  return request("/rate", {
    method: "POST",
    body: JSON.stringify({ run_id: runId, ...rating })
  });
}

export function getExportUrl(runId, format) {
  return `${apiBase()}/export/${runId}/${format}`;
}

export function listExperiments() {
  return request("/experiments?limit=20");
}

export function importMusicXmlToScoreDocument(musicxml, prompt = "") {
  return request("/score/import_musicxml", {
    method: "POST",
    body: JSON.stringify({ musicxml, prompt })
  });
}

export function exportScoreMusicXml(scoreDocument) {
  return request("/score/export_musicxml", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function exportScoreMidi(scoreDocument) {
  return request("/score/export_midi", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function exportScorePdf(scoreDocument) {
  return request("/score/export_pdf", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function validateScoreDocument(scoreDocument) {
  return request("/score/validate", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function applyWorkbenchOperation(scoreDocument, operation, operationHistory) {
  return request("/score/apply_operation", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      operation,
      operation_history: operationHistory
    })
  });
}

export function undoWorkbenchOperation(scoreDocument, operationHistory) {
  return request("/score/undo", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, operation_history: operationHistory })
  });
}

export function redoWorkbenchOperation(scoreDocument, operationHistory) {
  return request("/score/redo", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, operation_history: operationHistory })
  });
}

export function requestAgentScoreEdit(scoreDocument, instruction, selectedRange, constraints = {}, context = {}) {
  return request("/score/agent_edit", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      instruction,
      selected_range: selectedRange,
      constraints,
      ...context
    })
  });
}

export function applyWorkbenchOperations(scoreDocument, operations, operationHistory) {
  return request("/score/batch_operations", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      operations,
      operation_history: operationHistory
    })
  });
}

export function lightValidateScore(scoreDocument, dirtyMeasures = []) {
  return request("/score/light_validate", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, dirty_measures: dirtyMeasures })
  });
}

export function fullValidateScore(scoreDocument) {
  return request("/score/full_validate", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function renderPreviewMusicXml(scoreDocument) {
  return request("/score/render_preview_musicxml", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function renderPreviewSvg(scoreDocument) {
  return request("/score/render_preview_svg", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function renderPreviewPng(scoreDocument) {
  return request("/score/render_preview_png", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function renderPreviewPdf(scoreDocument) {
  return request("/score/render_preview_pdf", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument })
  });
}

export function generateLeftHandAccompaniment(scoreDocument, selectedRange, texture = "arpeggiated") {
  return request("/score/generate_accompaniment", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, selected_range: selectedRange, texture })
  });
}

export function migrateScoreProject(project) {
  return request("/score/migrate_project", {
    method: "POST",
    body: JSON.stringify({ project })
  });
}

export function exportProjectPackage(project) {
  return request("/score/export_project_package", {
    method: "POST",
    body: JSON.stringify({ project })
  });
}

export function revertLastAgentPatch(scoreDocument, operationHistory, patchHistory = []) {
  return request("/score/revert_last_agent_patch", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, operation_history: operationHistory, patch_history: patchHistory })
  });
}

export function continueFromLastEdit(scoreDocument, selectedRange, recentOperations = [], constraints = {}) {
  return request("/score/continue_from_last_edit", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, selected_range: selectedRange, recent_operations: recentOperations, constraints })
  });
}

export function previewScorePatch(scoreDocument, patch, instruction, selectedRange, constraints = {}) {
  return request("/score/preview_patch", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      patch,
      instruction,
      selected_range: selectedRange,
      constraints
    })
  });
}

export function validateScorePatch(scoreDocument, patch, instruction, selectedRange, constraints = {}) {
  return request("/score/validate_patch", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      patch,
      instruction,
      selected_range: selectedRange,
      constraints
    })
  });
}

export function generateStrictScorePatchPreview(scoreDocument, instruction, targetScope, protectedScope = {}) {
  return request("/sera-edit/generate-preview", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      instruction,
      target_scope: targetScope,
      protected_scope: protectedScope
    })
  });
}

export function previewCompositionCandidates(
  scoreDocument,
  brief,
  targetScope,
  protectedScope = {},
  candidateCount = 3,
  seed = 42,
  plannerMode = "auto"
) {
  return request("/sera-edit/composer/preview", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      brief,
      target_scope: targetScope,
      protected_scope: protectedScope,
      candidate_count: candidateCount,
      seed,
      planner_mode: plannerMode
    }),
    timeoutMs: 20000
  });
}

export function getCompositionRefinement(jobId) {
  return request(`/sera-edit/composer/refinements/${encodeURIComponent(jobId)}`, {
    timeoutMs: 5000
  });
}

export function submitCompositionPreference(feedback) {
  return request("/sera-edit/composer/feedback", {
    method: "POST",
    body: JSON.stringify(feedback)
  });
}

export function getCompositionPreferenceProfile() {
  return request("/sera-edit/composer/preference-profile");
}

export function getComposerStyleKnowledgeStatus() {
  return request("/sera-edit/composer/style-knowledge");
}

export function chatWithSera(message, history = [], scoreDocument = null, targetScope = {}) {
  return request("/sera-edit/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      history,
      score_document: scoreDocument,
      target_scope: targetScope
    })
  });
}

export function getSeraEditProviderStatus() {
  return request("/sera-edit/provider-status");
}

export function saveSeraEditProviderConfiguration(configuration) {
  return request("/sera-edit/provider-configuration", {
    method: "PUT",
    body: JSON.stringify(configuration)
  });
}

export function clearSeraEditProviderConfiguration() {
  return request("/sera-edit/provider-configuration", { method: "DELETE" });
}

export function validateStrictScorePatch(scoreDocument, patch) {
  return request("/sera-edit/schema-validate", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, patch })
  });
}

export function previewStrictScorePatch(scoreDocument, patch) {
  return request("/sera-edit/preview", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, patch })
  });
}

export function applyStrictScorePatch(scoreDocument, patch) {
  return request("/sera-edit/apply", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, patch })
  });
}

export function applyScorePatch(scoreDocument, patch, instruction, selectedRange, constraints = {}) {
  return request("/score/apply_patch", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      patch,
      instruction,
      selected_range: selectedRange,
      constraints
    })
  });
}

export function partialApplyScorePatch(scoreDocument, patch, instruction, selectedRange, constraints = {}, options = {}) {
  return request("/score/partial_apply_patch", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      patch,
      instruction,
      selected_range: selectedRange,
      constraints,
      operation_ids: options.operation_ids || [],
      operation_indexes: options.operation_indexes || [],
      apply_filter: options.apply_filter || "selected"
    })
  });
}

export function rejectScorePatch(scoreDocument, patch, reason = "Rejected in workbench") {
  return request("/score/reject_patch", {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, patch, reason })
  });
}

export function explainSelection(scoreDocument, selectedRange, question = "") {
  return request("/score/explain_selection", {
    method: "POST",
    body: JSON.stringify({
      score_document: scoreDocument,
      selected_range: selectedRange,
      question
    })
  });
}

export function getRenderCapabilities() {
  return request("/score/render_capabilities");
}

export function getBackendCapabilities() {
  return request("/capabilities");
}

export function getRendererStatus() {
  return request("/score/renderer_status");
}

export function getWorkbenchHealth() {
  return request("/score/workbench_health");
}

export function getNotationHosts() {
  return request("/integrations/notation-hosts");
}

export function createNotationBridgeSession(hostId, musicxml, sourceName = "imported.musicxml", prompt = "") {
  return request("/integrations/notation-sessions", {
    method: "POST",
    body: JSON.stringify({ host_id: hostId, musicxml, source_name: sourceName, prompt })
  });
}

export function getNotationBridgeWorkspace(sessionId) {
  return request(`/integrations/notation-sessions/${encodeURIComponent(sessionId)}/workspace`);
}

export function exportNotationBridgeRevision(sessionId, scoreDocument, expectedRevision) {
  return request(`/integrations/notation-sessions/${encodeURIComponent(sessionId)}/export`, {
    method: "POST",
    body: JSON.stringify({ score_document: scoreDocument, expected_revision: expectedRevision })
  });
}

export function saveScoreProject(projectId, project) {
  return request("/score/save_project", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, project })
  });
}

export function loadScoreProject(projectId) {
  return request("/score/load_project", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId })
  });
}

export function getBenchmarkReviewSummary() {
  return request("/sera-edit/review/summary");
}

export function listBenchmarkReviewTasks(filters = {}) {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.status) params.set("status", filters.status);
  if (filters.runtime_status) params.set("runtime_status", filters.runtime_status);
  if (filters.search) params.set("search", filters.search);
  const query = params.toString();
  return request(`/sera-edit/review/tasks${query ? `?${query}` : ""}`);
}

export function getBenchmarkReviewTask(taskId) {
  return request(`/sera-edit/review/tasks/${encodeURIComponent(taskId)}`);
}

export function submitBenchmarkReview(review) {
  return request("/sera-edit/review/decisions", {
    method: "POST",
    body: JSON.stringify(review)
  });
}

export function prepareBenchmarkReviewArtifact(taskId, variant) {
  return request(
    `/sera-edit/review/tasks/${encodeURIComponent(taskId)}/artifacts/${encodeURIComponent(variant)}`,
    { method: "POST" }
  );
}

export function exportBenchmarkReviews() {
  return request("/sera-edit/review/export", { method: "POST" });
}
