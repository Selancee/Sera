import { LEFT_STAFF_TOP, STAFF_TOP } from "./renderers/layoutMapping";

export type StaffLane = {
  staff: "right_hand" | "left_hand";
  label: string;
  clef: "treble" | "bass";
  y1: number;
  y2: number;
  center: number;
};

export const DEFAULT_STAFF_LANES: StaffLane[] = [
  { staff: "right_hand", label: "Right Hand", clef: "treble", y1: 42, y2: 126, center: STAFF_TOP + 18 },
  { staff: "left_hand", label: "Left Hand", clef: "bass", y1: 126, y2: 194, center: LEFT_STAFF_TOP + 18 }
];

export function staffLaneFromY(y: number, measureTop = 42): StaffLane {
  const lanes = staffLanesForMeasureTop(measureTop);
  return lanes.find((lane) => y >= lane.y1 && y <= lane.y2) || (y > lanes[0].y2 ? lanes[1] : lanes[0]);
}

export function staffAndPitchFromPoint(point: { x: number; y: number }, measureTop = 42) {
  const lane = staffLaneFromY(point.y, measureTop);
  return { staff: lane.staff, pitch: pitchFromY(point.y, lane.staff, measureTop), lane };
}

export function nextStaff(staff: "right_hand" | "left_hand", reverse = false): "right_hand" | "left_hand" {
  if (reverse) return staff === "right_hand" ? "left_hand" : "right_hand";
  return staff === "right_hand" ? "left_hand" : "right_hand";
}

export function pitchFromY(y: number, staff: "right_hand" | "left_hand", measureTop = 42): string {
  const rightTop = measureTop + (STAFF_TOP - 42);
  const leftTop = measureTop + (LEFT_STAFF_TOP - 42);
  if (staff === "left_hand") {
    const pitches = ["C2", "D2", "E2", "F2", "G2", "A2", "B2", "C3", "D3", "E3", "F3", "G3"];
    return pitches[Math.max(0, Math.min(pitches.length - 1, Math.round((leftTop + 42 - y) / 6) + 5))];
  }
  const pitches = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5"];
  return pitches[Math.max(0, Math.min(pitches.length - 1, Math.round((rightTop + 36 - y) / 6) + 2))];
}

export function staffLanesForMeasureTop(measureTop: number): StaffLane[] {
  const shift = measureTop - 42;
  return DEFAULT_STAFF_LANES.map((lane) => ({
    ...lane,
    y1: lane.y1 + shift,
    y2: lane.y2 + shift,
    center: lane.center + shift
  }));
}
