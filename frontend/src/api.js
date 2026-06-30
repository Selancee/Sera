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

export function generateScore(prompt, options = {}) {
  return request("/generate", {
    method: "POST",
    body: JSON.stringify({ prompt, ...options })
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
  return `${API_BASE}/export/${runId}/${format}`;
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

export function getWorkbenchHealth() {
  return request("/score/workbench_health");
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
