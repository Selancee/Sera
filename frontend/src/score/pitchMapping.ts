import { LEFT_STAFF_TOP, STAFF_TOP } from "./renderers/layoutMapping";

export type StaffLayoutInfo = {
  top: number;
  lineSpacing: number;
  y1?: number;
  y2?: number;
};

export type PitchResult = {
  pitch: string;
  midi: number;
  staffPosition: number;
  confidence: "high" | "medium" | "low";
  accidental?: "sharp" | "flat" | "natural";
};

const TREBLE_STEPS = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5", "A5"];
const BASS_STEPS = ["E2", "F2", "G2", "A2", "B2", "C3", "D3", "E3", "F3", "G3", "A3", "B3", "C4"];

export function defaultStaffLayout(staffId: string, clef: "treble" | "bass"): StaffLayoutInfo {
  const top = clef === "bass" || staffId === "left_hand" ? LEFT_STAFF_TOP : STAFF_TOP;
  return { top, lineSpacing: 9, y1: top - 32, y2: top + 52 };
}

export function mapYToPitch(params: {
  y: number;
  staffId: string;
  clef: "treble" | "bass";
  keySignature?: string;
  staffLayout: StaffLayoutInfo;
  accidentalMode?: "none" | "sharp" | "flat" | "natural";
}): PitchResult {
  const layout = params.staffLayout;
  const steps = params.clef === "bass" || params.staffId === "left_hand" ? BASS_STEPS : TREBLE_STEPS;
  const centerIndex = params.clef === "bass" || params.staffId === "left_hand" ? 6 : 4;
  const staffPosition = Math.round(((layout.top + layout.lineSpacing * 4 - params.y) / (layout.lineSpacing / 2)) * 2) / 2;
  const index = clamp(Math.round(centerIndex + staffPosition), 0, steps.length - 1);
  const pitch = applyAccidental(steps[index], params.accidentalMode);
  return {
    pitch,
    midi: pitchToMidi(pitch),
    staffPosition,
    confidence: confidenceForY(params.y, layout),
    accidental: params.accidentalMode && params.accidentalMode !== "none" ? params.accidentalMode : undefined
  };
}

export function pitchToMidi(pitch: string): number {
  const match = String(pitch || "C4").match(/^([A-G])([#b]?)(-?\d+)$/);
  if (!match) return 60;
  const pc: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  return (Number(match[3]) + 1) * 12 + pc[match[1]] + (match[2] === "#" ? 1 : match[2] === "b" ? -1 : 0);
}

function applyAccidental(pitch: string, accidentalMode: "none" | "sharp" | "flat" | "natural" = "none") {
  const match = pitch.match(/^([A-G])([#b]?)(-?\d+)$/);
  if (!match || accidentalMode === "none") return pitch;
  const accidental = accidentalMode === "sharp" ? "#" : accidentalMode === "flat" ? "b" : "";
  return `${match[1]}${accidental}${match[3]}`;
}

function confidenceForY(y: number, layout: StaffLayoutInfo): PitchResult["confidence"] {
  const y1 = layout.y1 ?? layout.top - 28;
  const y2 = layout.y2 ?? layout.top + layout.lineSpacing * 4 + 28;
  if (y >= y1 && y <= y2) return "high";
  if (y >= y1 - 18 && y <= y2 + 18) return "medium";
  return "low";
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
