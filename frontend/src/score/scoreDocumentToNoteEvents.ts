import type { ScoreDocument } from "./scoreTypes";

export type PlaybackNoteEvent = {
  event_id: string;
  measure_id: string;
  measure_number: number;
  staff: string;
  voice: number;
  pitch: string;
  midi: number;
  duration: string;
  duration_seconds: number;
  offset_beats: number;
  start_seconds: number;
  dynamic: string;
  diagnostic_stream: "playback_event_stream";
  melody_diagnostic_eligible: false;
};

export function scoreDocumentToNoteEvents(scoreDocument: ScoreDocument | null | undefined): PlaybackNoteEvent[] {
  if (!scoreDocument?.measures?.length) return [];
  const tempo = Number(scoreDocument.global?.tempo || 90);
  const secondsPerQuarter = 60 / Math.max(1, tempo);
  const measureQuarters = measureCapacity(scoreDocument.global?.meter || "4/4");
  const events: PlaybackNoteEvent[] = [];
  scoreDocument.measures.forEach((measure) => {
    const measureStart = (Number(measure.number || 1) - 1) * measureQuarters;
    measure.events.forEach((event) => {
      if (event.type === "rest") return;
      const midi = pitchToMidi(event.pitch);
      if (midi == null) return;
      const durationQuarters = durationToQuarters(event.duration);
      const offset = Number(event.offset || 0);
      events.push({
        event_id: event.event_id,
        measure_id: measure.measure_id,
        measure_number: measure.number,
        staff: event.staff,
        voice: event.voice,
        pitch: event.pitch,
        midi,
        duration: event.duration,
        duration_seconds: round(durationQuarters * secondsPerQuarter),
        offset_beats: offset,
        start_seconds: round((measureStart + offset) * secondsPerQuarter),
        dynamic: event.dynamic || "mf",
        diagnostic_stream: "playback_event_stream",
        melody_diagnostic_eligible: false
      });
    });
  });
  return events.sort((a, b) => a.start_seconds - b.start_seconds || a.midi - b.midi);
}

function measureCapacity(meter: string) {
  const [beats, beatType] = String(meter || "4/4").split("/").map((part) => Number(part) || 4);
  return beats * (4 / beatType);
}

function durationToQuarters(duration: string) {
  return {
    whole: 4,
    half: 2,
    quarter: 1,
    eighth: 0.5,
    sixteenth: 0.25,
    dotted_half: 3,
    dotted_quarter: 1.5,
    dotted_eighth: 0.75
  }[duration] || 1;
}

function pitchToMidi(pitch: string) {
  const match = String(pitch || "").match(/^([A-G])([#b]?)(-?\d)$/);
  if (!match) return null;
  const semitone: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const accidental = match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0;
  return (Number(match[3]) + 1) * 12 + semitone[match[1]] + accidental;
}

function round(value: number) {
  return Math.round(value * 10000) / 10000;
}
