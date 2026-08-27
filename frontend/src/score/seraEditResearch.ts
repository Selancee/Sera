import type {
  ScoreDocument,
  StrictScorePatch,
  StrictScoreScope,
  StrictValidationReport
} from "./scoreTypes";

type SelectedRange = { start_measure: number; end_measure: number };
type AgentConstraints = { target_staff?: string; target_voice?: string };

export type StrictPatchHistoryEntry = {
  patch: StrictScorePatch;
  beforeScore: ScoreDocument;
  afterScore: ScoreDocument;
  validationReport: StrictValidationReport;
};

export type StrictPatchHistory = {
  done: StrictPatchHistoryEntry[];
  undone: StrictPatchHistoryEntry[];
};

export const EMPTY_STRICT_PATCH_HISTORY: StrictPatchHistory = { done: [], undone: [] };

export function buildStrictScoreScopes(
  selectedRange: SelectedRange,
  eventIds: string[],
  constraints: AgentConstraints
): { targetScope: StrictScoreScope; protectedScope: StrictScoreScope } {
  const start = Math.max(1, Number(selectedRange.start_measure) || 1);
  const end = Math.max(start, Number(selectedRange.end_measure) || start);
  const measures = Array.from({ length: end - start + 1 }, (_, index) => start + index);
  const targetStaff = constraints.target_staff;
  const targetVoice = Number(constraints.target_voice);
  const targetScope: StrictScoreScope = eventIds.length
    ? { event_ids: [...eventIds] }
    : { measures };

  if (targetStaff === "right_hand" || targetStaff === "left_hand") {
    targetScope.staffs = [targetStaff];
  }
  if (Number.isInteger(targetVoice) && targetVoice > 0) {
    targetScope.voices = [targetVoice];
  }

  const protectedScope: StrictScoreScope = {};
  if (targetStaff === "right_hand") protectedScope.staffs = ["left_hand"];
  if (targetStaff === "left_hand") protectedScope.staffs = ["right_hand"];
  return { targetScope, protectedScope };
}

export function measureRangeForScope(
  scoreDocument: ScoreDocument,
  scope: StrictScoreScope,
  fallback: SelectedRange
): SelectedRange {
  const measures = new Set((scope.measures || []).map(Number));
  const eventIds = new Set(scope.event_ids || []);
  if (eventIds.size) {
    for (const measure of scoreDocument.measures) {
      if (measure.events.some((event) => eventIds.has(event.event_id))) measures.add(measure.number);
    }
  }
  const ordered = [...measures].filter(Number.isFinite).sort((a, b) => a - b);
  return ordered.length
    ? { start_measure: ordered[0], end_measure: ordered[ordered.length - 1] }
    : fallback;
}

export function recordStrictPatch(
  history: StrictPatchHistory,
  entry: StrictPatchHistoryEntry
): StrictPatchHistory {
  return { done: [...history.done, entry], undone: [] };
}

export function undoStrictPatch(
  history: StrictPatchHistory,
  currentScore: ScoreDocument
): null | { scoreDocument: ScoreDocument; history: StrictPatchHistory; validationReport: StrictValidationReport } {
  const entry = history.done[history.done.length - 1];
  if (!entry || entry.afterScore !== currentScore) return null;
  return {
    scoreDocument: entry.beforeScore,
    history: { done: history.done.slice(0, -1), undone: [...history.undone, entry] },
    validationReport: entry.validationReport
  };
}

export function redoStrictPatch(
  history: StrictPatchHistory,
  currentScore: ScoreDocument
): null | { scoreDocument: ScoreDocument; history: StrictPatchHistory; validationReport: StrictValidationReport } {
  const entry = history.undone[history.undone.length - 1];
  if (!entry || entry.beforeScore !== currentScore) return null;
  return {
    scoreDocument: entry.afterScore,
    history: { done: [...history.done, entry], undone: history.undone.slice(0, -1) },
    validationReport: entry.validationReport
  };
}
