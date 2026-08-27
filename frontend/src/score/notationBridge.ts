import { EMPTY_SELECTION, type ScoreSelection } from "./selection";
import type { ScoreDocument } from "./scoreTypes";

export function bridgeSessionIdFromSearch(search: string) {
  const value = new URLSearchParams(search).get("bridge_session") || "";
  return safeBridgeSessionId(value);
}

export function safeBridgeSessionId(value: unknown) {
  const normalized = String(value || "");
  return /^bridge_[A-Za-z0-9_-]{8,80}$/.test(normalized) ? normalized : "";
}

export function selectionFromNotationHostContext(score: ScoreDocument, hostContext: any): ScoreSelection {
  const hostSelection = hostContext?.selection || {};
  const start = Number(hostSelection.start_measure);
  const end = Number(hostSelection.end_measure);
  if (hostSelection.is_range && Number.isFinite(start) && Number.isFinite(end)) {
    const minimum = Math.min(start, end);
    const maximum = Math.max(start, end);
    const measureIds = score.measures
      .filter((measure) => measure.number >= minimum && measure.number <= maximum)
      .map((measure) => measure.measure_id);
    if (measureIds.length) {
      return { ...EMPTY_SELECTION, measureIds, anchorMeasureId: measureIds[0] };
    }
  }
  const firstMeasureId = score.measures[0]?.measure_id || "";
  return { ...EMPTY_SELECTION, measureIds: firstMeasureId ? [firstMeasureId] : [], anchorMeasureId: firstMeasureId };
}
