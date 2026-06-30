import type { OperationHistory, ScoreOperation } from "./scoreTypes";

export const EMPTY_OPERATION_HISTORY: OperationHistory = { done: [], undone: [] };

export function summarizeOperation(operation: ScoreOperation): string {
  return operation.description || operation.type.replaceAll("_", " ");
}

export function serializeOperationHistory(history: OperationHistory) {
  return JSON.stringify(history, null, 2);
}

