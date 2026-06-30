import type { ScoreEvent } from "./scoreTypes";

export function pitchToStaffY(event: ScoreEvent) {
  const pitch = event.pitch || "C4";
  const step = pitch[0]?.toUpperCase() || "C";
  const octave = Number(pitch.match(/\d/)?.[0] || 4);
  const stepMap: Record<string, number> = { C: 112, D: 107, E: 102, F: 97, G: 92, A: 87, B: 82 };
  return (stepMap[step] || 102) - (octave - 4) * 28;
}

