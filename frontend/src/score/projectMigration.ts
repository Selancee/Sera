import { EMPTY_OPERATION_HISTORY } from "./operationHistory";
import { createEmptyScoreDocument, type WorkbenchProject } from "./scoreTypes";

export function migrateWorkbenchProject(input: any): WorkbenchProject {
  const project = input || {};
  const scoreDocument = project.score_document || project.ScoreDocument || project.scoreDocument || createEmptyScoreDocument();
  const operationHistory = project.operation_history || project.OperationHistory || project.operationHistory || EMPTY_OPERATION_HISTORY;
  return {
    project_version: "0.8",
    score_document: { ...scoreDocument, metadata: { ...(scoreDocument.metadata || {}), workbench_version: "0.8" } },
    operation_history: {
      done: Array.isArray(operationHistory.done) ? operationHistory.done : [],
      undone: Array.isArray(operationHistory.undone) ? operationHistory.undone : []
    },
    agent_patch_history: project.agent_patch_history || project.AgentPatchHistory || project.agentPatchHistory || [],
    original_prompt: project.original_prompt || project.OriginalPrompt || project.originalPrompt || "",
    composition_plan: project.composition_plan || project.CompositionPlan || project.compositionPlan || {},
    validation_reports: project.validation_reports || project.ValidationReports || project.validationReports || [],
    export_metadata: project.export_metadata || project.ExportMetadata || project.exportMetadata || {},
    experiment_metadata: project.experiment_metadata || project.ExperimentMetadata || project.experimentMetadata || {},
    autosaved_at: project.autosaved_at
  };
}

export function projectNeedsMigration(input: any) {
  return !input || input.project_version !== "0.8";
}
