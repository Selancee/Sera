import type { ScoreDocument, ScoreEvent, ScoreOperation } from "./scoreTypes";

const STEP_PIXELS = 8;
const OFFSET_PIXELS = 38;

export type DragPreview = {
  eventIds: string[];
  semitones: number;
  offsetDelta: number;
  previewPitches: string[];
  warning: string;
};

export function semitonesFromVerticalDrag(deltaY: number) {
  return Math.max(-24, Math.min(24, Math.round(-deltaY / STEP_PIXELS)));
}

export function offsetDeltaFromHorizontalDrag(deltaX: number, grid = 0.25) {
  const raw = Math.round(deltaX / OFFSET_PIXELS) * grid;
  return Math.max(-4, Math.min(4, raw));
}

export function createDragPreview(score: ScoreDocument, eventIds: string[], deltaY: number, deltaX = 0): DragPreview {
  const semitones = semitonesFromVerticalDrag(deltaY);
  const offsetDelta = offsetDeltaFromHorizontalDrag(deltaX);
  const events = findEvents(score, eventIds);
  return {
    eventIds,
    semitones,
    offsetDelta,
    previewPitches: events.map((event) => (event.type === "note" ? transposePitch(event.pitch, semitones) : "rest")),
    warning: Math.abs(offsetDelta) > 0 ? "Horizontal drag will quantize offset to the nearest grid." : ""
  };
}

export function buildDragOperations(score: ScoreDocument, eventIds: string[], deltaY: number, deltaX = 0, duplicate = false): ScoreOperation[] {
  const semitones = semitonesFromVerticalDrag(deltaY);
  const offsetDelta = offsetDeltaFromHorizontalDrag(deltaX);
  const events = findEvents(score, eventIds);
  const operations: ScoreOperation[] = [];
  for (const item of events) {
    if (duplicate) {
      operations.push({
        source: "user",
        type: item.event.type === "rest" ? "insert_rest" : "insert_note",
        target: { measure_id: item.measure.measure_id, measure: item.measure.number, staff: item.event.staff, voice: item.event.voice },
        after: {
          ...item.event,
          event_id: `${item.event.event_id}_copy_${Date.now().toString(36)}`,
          pitch: item.event.type === "note" ? transposePitch(item.event.pitch, semitones) : "",
          offset: quantizeOffset(item.event.offset + offsetDelta)
        },
        description: "Alt-drag duplicate note"
      });
      continue;
    }
    if (item.event.type === "note" && semitones !== 0) {
      operations.push({
        source: "user",
        type: "update_pitch",
        target: { measure_id: item.measure.measure_id, measure: item.measure.number, event_id: item.event.event_id },
        after: { pitch: transposePitch(item.event.pitch, semitones) },
        description: `Drag pitch ${semitones > 0 ? "up" : "down"} ${Math.abs(semitones)} semitone(s)`
      });
    }
    if (offsetDelta !== 0) {
      operations.push({
        source: "user",
        type: "move_note",
        target: { measure_id: item.measure.measure_id, measure: item.measure.number, event_id: item.event.event_id },
        after: { offset: quantizeOffset(item.event.offset + offsetDelta) },
        description: "Drag note offset"
      });
    }
  }
  return operations;
}

export function transposePitch(pitch: string, semitones: number) {
  const midi = pitchToMidi(pitch);
  if (midi === null) return pitch;
  return midiToPitch(Math.max(21, Math.min(108, midi + semitones)));
}

export function pitchToMidi(pitch: string): number | null {
  const match = String(pitch || "").match(/^([A-G])([#b]?)(-?\d+)$/i);
  if (!match) return null;
  const stepMap: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const step = stepMap[match[1].toUpperCase()] ?? 0;
  const accidental = match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0;
  const octave = Number(match[3]);
  return (octave + 1) * 12 + step + accidental;
}

export function midiToPitch(midi: number) {
  const octave = Math.floor(midi / 12) - 1;
  const names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
  return `${names[((midi % 12) + 12) % 12]}${octave}`;
}

function findEvents(score: ScoreDocument, eventIds: string[]) {
  const wanted = new Set(eventIds);
  const found: Array<{ measure: ScoreDocument["measures"][number]; event: ScoreEvent }> = [];
  for (const measure of score.measures) {
    for (const event of measure.events) {
      if (wanted.has(event.event_id)) found.push({ measure, event });
    }
  }
  return found;
}

function quantizeOffset(offset: number) {
  return Math.max(0, Math.round(offset * 4) / 4);
}
