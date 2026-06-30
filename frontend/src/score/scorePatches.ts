import { applyLocalOperation } from "./scoreOperations";
import { computeScoreDiff } from "./scoreDiff";
import type { ScoreDocument, ScoreOperation, ScorePatch } from "./scoreTypes";

export function previewLocalPatch(scoreDocument: ScoreDocument, patch: ScorePatch) {
  let current = scoreDocument;
  const operations = [];
  for (const operation of patch.operations || []) {
    const applied = applyLocalOperation(current, operation);
    current = applied.scoreDocument;
    operations.push(applied.operation);
  }
  return {
    patch: { ...patch, operations },
    before_score_document: scoreDocument,
    after_score_document: current,
    diff: computeScoreDiff(scoreDocument, current, { ...patch, operations })
  };
}

export function createPartialPatch(patch: ScorePatch, operationIndexes: number[]) {
  const wanted = new Set(operationIndexes);
  return {
    ...patch,
    patch_id: `${patch.patch_id}_partial`,
    operations: patch.operations.filter((_, index) => wanted.has(index)),
    rationale: `Partial apply: ${patch.rationale}`
  };
}

export function filterOperationsByKind(operations: ScoreOperation[], kind: "all" | "notes" | "dynamics" | "harmony" | "measures") {
  if (kind === "all") return operations;
  const sets: Record<string, Set<string>> = {
    notes: new Set(["insert_note", "delete_note", "update_pitch", "update_duration", "move_note", "transpose_selection"]),
    dynamics: new Set(["change_dynamic"]),
    harmony: new Set(["add_harmony_label", "update_harmony", "add_cadence"]),
    measures: new Set(["insert_measure", "delete_measure", "duplicate_measure", "regenerate_selected_measures"])
  };
  return operations.filter((operation) => sets[kind]?.has(operation.type));
}

export function patchCanAccept(preview: any) {
  const report = preview?.patch_validation_report;
  if (!report) return Boolean(preview?.validation_report?.valid_musicxml ?? preview?.patch);
  return Boolean(report.valid && report.recommendation !== "reject");
}
