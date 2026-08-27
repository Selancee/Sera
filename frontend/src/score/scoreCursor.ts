import type { NoteDuration, NoteInputCursor } from "./noteInput";
import { DEFAULT_NOTE_INPUT_CURSOR, durationToQuarters, measureCapacity as noteMeasureCapacity } from "./noteInput";
import type { ScoreDocument } from "./scoreTypes";
import { beatFromOffset, measureCapacity, snapOffset, snapSizeForMeter } from "./scoreGrid";

export type ScoreCursorMode = "select" | "note_input" | "rhythm_input" | "chord_input";
export type ScoreCursorSnap = "beat" | "eighth" | "sixteenth" | "triplet";
export type ScoreCursorStaff = "right_hand" | "left_hand";

export type ScoreCursor = {
  measure_id: string;
  measure_number: number;
  staff: ScoreCursorStaff;
  voice: 1 | 2;
  beat: number;
  offset: number;
  duration: NoteDuration;
  pitch: string;
  mode: ScoreCursorMode;
  snap: ScoreCursorSnap;
  valid: boolean;
  warning?: string;
};

export const DEFAULT_SCORE_CURSOR: ScoreCursor = {
  measure_id: "m1",
  measure_number: 1,
  staff: "right_hand",
  voice: 1,
  beat: 1,
  offset: 0,
  duration: "quarter",
  pitch: "C4",
  mode: "select",
  snap: "beat",
  valid: true
};

export function scoreCursorFromNoteInput(cursor: NoteInputCursor, mode: "select" | "note_input", score: ScoreDocument, snap: ScoreCursorSnap = "beat"): ScoreCursor {
  const duration = cursor.dotted && !cursor.duration.startsWith("dotted_") ? (`dotted_${cursor.duration}` as NoteDuration) : cursor.duration;
  return validateScoreCursor(score, {
    measure_id: cursor.measureId,
    measure_number: cursor.measureNumber,
    staff: cursor.staff,
    voice: cursor.voice,
    beat: beatFromOffset(cursor.offset, score.global.meter),
    offset: cursor.offset,
    duration,
    pitch: `${cursor.staff === "left_hand" ? "C3" : "C"}${cursor.octave}`,
    mode,
    snap,
    valid: true
  });
}

export function noteInputFromScoreCursor(cursor: ScoreCursor, previous: NoteInputCursor = DEFAULT_NOTE_INPUT_CURSOR): NoteInputCursor {
  const octave = Number(String(cursor.pitch || previous.octave).match(/\d/)?.[0] || previous.octave);
  const duration = String(cursor.duration || previous.duration);
  return {
    ...previous,
    measureId: cursor.measure_id,
    measureNumber: cursor.measure_number,
    staff: cursor.staff,
    voice: cursor.voice,
    offset: cursor.offset,
    duration: duration.replace("dotted_", "") as NoteDuration,
    dotted: duration.startsWith("dotted_"),
    octave
  };
}

export function validateScoreCursor(score: ScoreDocument, cursor: ScoreCursor): ScoreCursor {
  const capacity = measureCapacity(score);
  const duration = durationToQuarters(cursor.duration, cursor.duration.startsWith("dotted_"));
  const measure = score.measures.find((item) => item.measure_id === cursor.measure_id || item.number === cursor.measure_number);
  const end = cursor.offset + duration;
  const valid = Boolean(measure) && cursor.offset >= 0 && end <= capacity + 0.001;
  return {
    ...cursor,
    beat: beatFromOffset(cursor.offset, score.global.meter),
    measure_id: measure?.measure_id || cursor.measure_id,
    measure_number: measure?.number || cursor.measure_number,
    valid,
    warning: valid ? "" : `Cursor is outside measure capacity (${noteMeasureCapacity(score)} quarters).`
  };
}

export function moveScoreCursor(score: ScoreDocument, cursor: ScoreCursor, steps: number): ScoreCursor {
  const meter = score.global.meter;
  const step = snapSizeForMeter(meter, cursor.snap);
  const capacity = measureCapacity(score);
  const measureIndex = score.measures.findIndex((measure) => measure.measure_id === cursor.measure_id);
  let nextMeasureIndex = Math.max(0, measureIndex);
  let nextOffset = snapOffset(cursor.offset + steps * step, meter, cursor.snap);

  while (nextOffset >= capacity - 0.0001 && nextMeasureIndex < score.measures.length - 1) {
    nextOffset = snapOffset(nextOffset - capacity, meter, cursor.snap);
    nextMeasureIndex += 1;
  }
  while (nextOffset < 0 && nextMeasureIndex > 0) {
    nextOffset = snapOffset(capacity + nextOffset, meter, cursor.snap);
    nextMeasureIndex -= 1;
  }
  nextOffset = Math.max(0, Math.min(capacity - step, nextOffset));
  const measure = score.measures[nextMeasureIndex] || score.measures[0];
  return validateScoreCursor(score, { ...cursor, measure_id: measure.measure_id, measure_number: measure.number, offset: nextOffset });
}

export function jumpScoreCursorMeasure(score: ScoreDocument, cursor: ScoreCursor, delta: number): ScoreCursor {
  const currentIndex = score.measures.findIndex((measure) => measure.measure_id === cursor.measure_id);
  const next = score.measures[Math.max(0, Math.min(score.measures.length - 1, currentIndex + delta))] || score.measures[0];
  return validateScoreCursor(score, { ...cursor, measure_id: next.measure_id, measure_number: next.number, offset: 0 });
}

export function jumpScoreCursorBoundary(score: ScoreDocument, cursor: ScoreCursor, boundary: "start" | "end"): ScoreCursor {
  const measure = boundary === "start" ? score.measures[0] : score.measures[score.measures.length - 1];
  const capacity = measureCapacity(score);
  return validateScoreCursor(score, { ...cursor, measure_id: measure.measure_id, measure_number: measure.number, offset: boundary === "start" ? 0 : Math.max(0, capacity - snapSizeForMeter(score.global.meter, cursor.snap)) });
}

export function transposeCursorPitch(cursor: ScoreCursor, semitones: number): ScoreCursor {
  return { ...cursor, pitch: transposePitchName(cursor.pitch, semitones) };
}

export function switchCursorStaff(cursor: ScoreCursor, reverse = false): ScoreCursor {
  const staff = reverse ? (cursor.staff === "right_hand" ? "left_hand" : "right_hand") : cursor.staff === "right_hand" ? "left_hand" : "right_hand";
  return { ...cursor, staff, pitch: staff === "left_hand" ? "C3" : "C4" };
}

export function switchCursorVoice(cursor: ScoreCursor): ScoreCursor {
  return { ...cursor, voice: cursor.voice === 1 ? 2 : 1 };
}

export function setScoreCursorDuration(cursor: ScoreCursor, duration: NoteDuration): ScoreCursor {
  return { ...cursor, duration };
}

export function toggleScoreCursorDotted(cursor: ScoreCursor): ScoreCursor {
  const duration = cursor.duration.startsWith("dotted_") ? (cursor.duration.replace("dotted_", "") as NoteDuration) : (`dotted_${cursor.duration}` as NoteDuration);
  return { ...cursor, duration };
}

function transposePitchName(pitch: string, semitones: number): string {
  const match = String(pitch || "C4").match(/^([A-G])([#b]?)(-?\d+)$/);
  if (!match) return pitch || "C4";
  const stepMap: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const midi = (Number(match[3]) + 1) * 12 + stepMap[match[1]] + (match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0) + semitones;
  const pcs: Array<[string, string]> = [["C", ""], ["C", "#"], ["D", ""], ["E", "b"], ["E", ""], ["F", ""], ["F", "#"], ["G", ""], ["A", "b"], ["A", ""], ["B", "b"], ["B", ""]];
  const [step, accidental] = pcs[((midi % 12) + 12) % 12];
  return `${step}${accidental}${Math.floor(midi / 12) - 1}`;
}
