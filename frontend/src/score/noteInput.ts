import type { ScoreDocument, ScoreOperation } from "./scoreTypes";
import type { ScoreSelection } from "./selection";

export type NoteDuration =
  | "whole"
  | "half"
  | "quarter"
  | "eighth"
  | "sixteenth"
  | "dotted_half"
  | "dotted_quarter"
  | "dotted_eighth"
  | "triplet_eighth";

export type NoteInputCursor = {
  measureId: string;
  measureNumber: number;
  staff: "right_hand" | "left_hand";
  voice: 1 | 2;
  offset: number;
  duration: NoteDuration;
  dotted: boolean;
  accidental: "" | "sharp" | "flat" | "natural";
  octave: number;
  chordMode: boolean;
};

export const DEFAULT_NOTE_INPUT_CURSOR: NoteInputCursor = {
  measureId: "m1",
  measureNumber: 1,
  staff: "right_hand",
  voice: 1,
  offset: 0,
  duration: "quarter",
  dotted: false,
  accidental: "",
  octave: 4,
  chordMode: false
};

export const DURATION_KEY_MAP: Record<string, NoteDuration> = {
  "1": "whole",
  "2": "half",
  "4": "quarter",
  "8": "eighth",
  "6": "sixteenth"
};

export const DURATION_TO_QUARTERS: Record<string, number> = {
  whole: 4,
  half: 2,
  quarter: 1,
  eighth: 0.5,
  sixteenth: 0.25,
  dotted_half: 3,
  dotted_quarter: 1.5,
  dotted_eighth: 0.75,
  triplet_eighth: 1 / 3
};

export function cursorFromSelection(score: ScoreDocument, selection: ScoreSelection, previous: NoteInputCursor = DEFAULT_NOTE_INPUT_CURSOR): NoteInputCursor {
  const selectedMeasure = score.measures.find((measure) => selection.measureIds.includes(measure.measure_id)) || score.measures[0];
  if (!selectedMeasure) return previous;
  const selectedEvent = selectedMeasure.events.find((event) => selection.eventIds.includes(event.event_id));
  const nextOffset = selectedEvent
    ? selectedEvent.offset
    : Math.min(measureCapacity(score), measureUsedQuarters(score, selectedMeasure.measure_id, previous.staff, previous.voice));
  return {
    ...previous,
    measureId: selectedMeasure.measure_id,
    measureNumber: selectedMeasure.number,
    staff: (selectedEvent?.staff as NoteInputCursor["staff"]) || previous.staff,
    voice: ((selectedEvent?.voice === 2 ? 2 : 1) as 1 | 2) || previous.voice,
    offset: nextOffset
  };
}

export function durationFromKey(key: string): NoteDuration | null {
  return DURATION_KEY_MAP[key] || null;
}

export function setCursorDuration(cursor: NoteInputCursor, duration: NoteDuration): NoteInputCursor {
  return { ...cursor, duration, dotted: duration.startsWith("dotted_") || cursor.dotted };
}

export function durationToQuarters(duration: string, dotted = false): number {
  const normalized = dotted && !String(duration).startsWith("dotted_") ? `dotted_${duration}` : duration;
  return DURATION_TO_QUARTERS[normalized] || DURATION_TO_QUARTERS[duration] || 1;
}

export function measureCapacity(score: ScoreDocument): number {
  const [beats, beatType] = String(score.global.meter || "4/4").split("/").map((value) => Number(value) || 4);
  return beats * (4 / beatType);
}

export function measureUsedQuarters(score: ScoreDocument, measureId: string, staff: string, voice: number): number {
  const measure = score.measures.find((item) => item.measure_id === measureId);
  if (!measure) return 0;
  return measure.events
    .filter((event) => event.staff === staff && Number(event.voice || 1) === Number(voice || 1))
    .reduce((max, event) => Math.max(max, Number(event.offset || 0) + durationToQuarters(event.duration)), 0);
}

export function canInsertAtCursor(score: ScoreDocument, cursor: NoteInputCursor) {
  const duration = durationToQuarters(cursor.duration, cursor.dotted);
  const capacity = measureCapacity(score);
  const end = cursor.offset + duration;
  return {
    ok: end <= capacity + 0.001,
    end,
    capacity,
    warning: end > capacity + 0.001 ? `Input exceeds measure ${cursor.measureNumber} capacity (${capacity} quarters).` : ""
  };
}

export function pitchFromStep(step: string, cursor: NoteInputCursor): string {
  const normalized = step.toUpperCase();
  const accidental = cursor.accidental === "sharp" ? "#" : cursor.accidental === "flat" ? "b" : "";
  return `${normalized}${accidental}${cursor.octave}`;
}

export function createInsertNoteOperation(score: ScoreDocument, cursor: NoteInputCursor, step: string, chordTone = false): ScoreOperation {
  const check = canInsertAtCursor(score, cursor);
  const offset = chordTone || cursor.chordMode ? cursor.offset : Math.min(cursor.offset, check.capacity);
  return {
    source: "user",
    type: "insert_note",
    target: { measure_id: cursor.measureId, measure: cursor.measureNumber, staff: cursor.staff, voice: cursor.voice },
    after: {
      event_id: `${cursor.measureId}_e${Date.now().toString(36)}`,
      pitch: pitchFromStep(step, cursor),
      duration: cursor.duration,
      offset,
      staff: cursor.staff,
      voice: cursor.voice,
      accidental: cursor.accidental,
      dynamic: "mf"
    },
    description: `Input ${pitchFromStep(step, cursor)}`
  };
}

export function createInsertRestOperation(score: ScoreDocument, cursor: NoteInputCursor): ScoreOperation {
  const check = canInsertAtCursor(score, cursor);
  return {
    source: "user",
    type: "insert_rest",
    target: { measure_id: cursor.measureId, measure: cursor.measureNumber, staff: cursor.staff, voice: cursor.voice },
    after: {
      event_id: `${cursor.measureId}_r${Date.now().toString(36)}`,
      duration: cursor.duration,
      offset: Math.min(cursor.offset, check.capacity),
      staff: cursor.staff,
      voice: cursor.voice
    },
    description: "Input rest"
  };
}

export function advanceCursor(score: ScoreDocument, cursor: NoteInputCursor): NoteInputCursor {
  if (cursor.chordMode) return cursor;
  const capacity = measureCapacity(score);
  const nextOffset = cursor.offset + durationToQuarters(cursor.duration, cursor.dotted);
  if (nextOffset < capacity - 0.001) return { ...cursor, offset: roundGrid(nextOffset) };
  const measureIndex = score.measures.findIndex((measure) => measure.measure_id === cursor.measureId);
  const nextMeasure = score.measures[Math.min(score.measures.length - 1, measureIndex + 1)] || score.measures[measureIndex];
  return { ...cursor, measureId: nextMeasure.measure_id, measureNumber: nextMeasure.number, offset: 0 };
}

export function fillMeasureWithRests(score: ScoreDocument, cursor: NoteInputCursor): ScoreOperation[] {
  const used = measureUsedQuarters(score, cursor.measureId, cursor.staff, cursor.voice);
  const capacity = measureCapacity(score);
  if (used >= capacity - 0.001) return [];
  return [
    {
      source: "system",
      type: "insert_rest",
      target: { measure_id: cursor.measureId, measure: cursor.measureNumber, staff: cursor.staff, voice: cursor.voice },
      after: { duration: quartersToDuration(capacity - used), offset: used, staff: cursor.staff, voice: cursor.voice },
      description: "Auto-fill remaining beats with a rest"
    }
  ];
}

export function quartersToDuration(quarters: number): NoteDuration {
  const entries = Object.entries(DURATION_TO_QUARTERS).sort((a, b) => Math.abs(b[1] - quarters) - Math.abs(a[1] - quarters));
  const exact = Object.entries(DURATION_TO_QUARTERS).find(([, value]) => Math.abs(value - quarters) < 0.01);
  return ((exact || entries[entries.length - 1])?.[0] || "quarter") as NoteDuration;
}

function roundGrid(value: number): number {
  return Math.round(value * 4) / 4;
}
