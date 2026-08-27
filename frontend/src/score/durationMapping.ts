import type { NoteDuration } from "./noteInput";
import { DURATION_TO_QUARTERS, measureCapacity } from "./noteInput";
import type { ScoreDocument, ScoreEvent } from "./scoreTypes";

export type DurationMappingResult = {
  duration: NoteDuration;
  dotted: boolean;
  quarters: number;
  valid: boolean;
  endOffset: number;
  capacity: number;
  clickAction: "insert_note" | "insert_rest" | "replace_rest" | "invalid";
  warning: string;
  replaceEventId?: string;
};

export function normalizeDuration(duration: string, dotted = false): NoteDuration {
  const clean = duration.replace("-", "_") as NoteDuration;
  if (clean.startsWith("dotted_")) return clean;
  if (dotted && canBeDotted(clean)) return `dotted_${clean}` as NoteDuration;
  return clean;
}

export function durationQuarters(duration: string, dotted = false): number {
  const normalized = normalizeDuration(duration, dotted);
  return DURATION_TO_QUARTERS[normalized] || DURATION_TO_QUARTERS[duration] || 1;
}

export function mapDurationForInsertion(params: {
  score: ScoreDocument;
  measureId: string;
  staff: string;
  voice: number;
  offset: number;
  duration: string;
  dotted?: boolean;
  insertingRest?: boolean;
}): DurationMappingResult {
  const duration = normalizeDuration(params.duration, Boolean(params.dotted));
  const quarters = durationQuarters(duration);
  const capacity = measureCapacity(params.score);
  const endOffset = round(params.offset + quarters);
  const rest = findReplaceableRest(params.score, params.measureId, params.staff, params.voice, params.offset, quarters);
  if (endOffset > capacity + 0.001) {
    return {
      duration,
      dotted: duration.startsWith("dotted_"),
      quarters,
      valid: false,
      endOffset,
      capacity,
      clickAction: "invalid",
      warning: `Insertion exceeds measure capacity by ${round(endOffset - capacity)} quarter units.`
    };
  }
  return {
    duration,
    dotted: duration.startsWith("dotted_"),
    quarters,
    valid: true,
    endOffset,
    capacity,
    clickAction: rest && !params.insertingRest ? "replace_rest" : params.insertingRest ? "insert_rest" : "insert_note",
    warning: "",
    replaceEventId: rest?.event_id
  };
}

function canBeDotted(duration: string) {
  return duration === "half" || duration === "quarter" || duration === "eighth";
}

function findReplaceableRest(score: ScoreDocument, measureId: string, staff: string, voice: number, offset: number, quarters: number): ScoreEvent | null {
  const measure = score.measures.find((item) => item.measure_id === measureId);
  if (!measure) return null;
  return (
    measure.events.find((event) => {
      if (event.type !== "rest") return false;
      if (event.staff !== staff || Number(event.voice || 1) !== Number(voice || 1)) return false;
      const eventStart = Number(event.offset || 0);
      const eventEnd = eventStart + durationQuarters(event.duration);
      return offset >= eventStart - 0.001 && offset + quarters <= eventEnd + 0.001;
    }) || null
  );
}

function round(value: number) {
  return Math.round(value * 1000) / 1000;
}
