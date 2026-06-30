import type { OperationHistory, ScoreDocument, ScorePatch, WorkbenchProject } from "./scoreTypes";

export const AUTOSAVE_KEY = "sera_v08_autosave";

export function makeAutosavePayload(args: {
  scoreDocument: ScoreDocument;
  operationHistory: OperationHistory;
  agentPatchHistory?: ScorePatch[];
  originalPrompt?: string;
  compositionPlan?: Record<string, unknown>;
  validationReports?: Array<Record<string, unknown>>;
  exportMetadata?: Record<string, unknown>;
  experimentMetadata?: Record<string, unknown>;
}): WorkbenchProject {
  return {
    project_version: "0.8",
    score_document: args.scoreDocument,
    operation_history: args.operationHistory,
    agent_patch_history: args.agentPatchHistory || [],
    original_prompt: args.originalPrompt || "",
    composition_plan: args.compositionPlan || {},
    validation_reports: args.validationReports || [],
    export_metadata: args.exportMetadata || {},
    experiment_metadata: args.experimentMetadata || {},
    autosaved_at: new Date().toISOString()
  };
}

export function saveAutosave(project: WorkbenchProject, storage: Storage | null = safeStorage()) {
  if (!storage) return false;
  storage.setItem(AUTOSAVE_KEY, JSON.stringify(project));
  return true;
}

export function loadAutosave(storage: Storage | null = safeStorage()): WorkbenchProject | null {
  if (!storage) return null;
  const raw = storage.getItem(AUTOSAVE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as WorkbenchProject;
  } catch {
    return null;
  }
}

export function clearAutosave(storage: Storage | null = safeStorage()) {
  storage?.removeItem(AUTOSAVE_KEY);
}

function safeStorage(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}
