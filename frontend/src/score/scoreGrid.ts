import { LEFT_STAFF_TOP, MEASURE_WIDTH, SCORE_LEFT, STAFF_TOP, pitchToStaffY } from "./renderers/layoutMapping";
import type { LayoutBox } from "./renderers/renderTypes";
import type { ScoreDocument, ScoreEvent } from "./scoreTypes";
import type { ScoreCursor, ScoreCursorSnap } from "./scoreCursor";

export type MeasureGridGeometry = {
  measureId: string;
  measureNumber: number;
  x: number;
  y: number;
  width: number;
  height: number;
  gridLeft: number;
  gridRight: number;
};

export type BeatGridPoint = {
  measureId: string;
  measureNumber: number;
  beat: number;
  offset: number;
  x: number;
  strong: boolean;
};

export function measureCapacity(score: Pick<ScoreDocument, "global"> | string): number {
  const meter = typeof score === "string" ? score : String(score.global?.meter || "4/4");
  const [beats, beatType] = meter.split("/").map((value) => Number(value) || 4);
  return beats * (4 / beatType);
}

export function snapSizeForMeter(meter: string, snap: ScoreCursorSnap): number {
  if (snap === "triplet") return 1 / 3;
  if (snap === "sixteenth") return 0.25;
  if (snap === "eighth") return 0.5;
  if (meter === "6/8") return 1.5;
  return 1;
}

export function snapOffset(offset: number, meter: string, snap: ScoreCursorSnap): number {
  const step = snapSizeForMeter(meter, snap);
  return roundGrid(Math.max(0, Math.round(offset / step) * step));
}

export function beatFromOffset(offset: number, meter: string): number {
  if (meter === "6/8") return roundGrid(offset / 1.5 + 1);
  return roundGrid(offset + 1);
}

export function buildMeasureGeometry(score: ScoreDocument, boxes: LayoutBox[] = []): MeasureGridGeometry[] {
  return score.measures.map((measure, index) => {
    const box = boxes.find((item) => item.type === "measure" && item.measureId === measure.measure_id);
    const fallbackX = index * MEASURE_WIDTH + SCORE_LEFT - 4;
    const x = Number(box?.x ?? fallbackX);
    const y = Number(box?.y ?? 42);
    const width = Number(box?.width ?? MEASURE_WIDTH - 10);
    const height = Number(box?.height ?? 152);
    return {
      measureId: measure.measure_id,
      measureNumber: measure.number,
      x,
      y,
      width,
      height,
      gridLeft: x + 18,
      gridRight: x + width - 16
    };
  });
}

export function buildBeatGrid(score: ScoreDocument, snap: ScoreCursorSnap = "beat", boxes: LayoutBox[] = []): BeatGridPoint[] {
  const meter = String(score.global?.meter || "4/4");
  const capacity = measureCapacity(score);
  const step = snapSizeForMeter(meter, snap);
  return buildMeasureGeometry(score, boxes).flatMap((geometry) => {
    const points: BeatGridPoint[] = [];
    for (let offset = 0; offset <= capacity + 0.0001; offset += step) {
      const snapped = roundGrid(offset);
      points.push({
        measureId: geometry.measureId,
        measureNumber: geometry.measureNumber,
        beat: beatFromOffset(snapped, meter),
        offset: snapped,
        x: offsetToX(geometry, snapped, capacity),
        strong: isStrongBeat(snapped, meter)
      });
    }
    return points;
  });
}

export function geometryAtPoint(score: ScoreDocument, point: { x: number; y: number }, boxes: LayoutBox[] = []): MeasureGridGeometry | null {
  return (
    buildMeasureGeometry(score, boxes).find((geometry) =>
      point.x >= geometry.x &&
      point.x <= geometry.x + geometry.width &&
      point.y >= geometry.y &&
      point.y <= geometry.y + geometry.height
    ) || null
  );
}

export function offsetFromX(geometry: MeasureGridGeometry, x: number, capacity: number): number {
  const width = Math.max(1, geometry.gridRight - geometry.gridLeft);
  const ratio = Math.max(0, Math.min(1, (x - geometry.gridLeft) / width));
  return roundGrid(ratio * capacity);
}

export function offsetToX(geometry: MeasureGridGeometry, offset: number, capacity: number): number {
  const ratio = capacity > 0 ? Math.max(0, Math.min(1, offset / capacity)) : 0;
  return geometry.gridLeft + (geometry.gridRight - geometry.gridLeft) * ratio;
}

export function cursorToPoint(score: ScoreDocument, cursor: ScoreCursor, boxes: LayoutBox[] = []) {
  const geometry = buildMeasureGeometry(score, boxes).find((item) => item.measureId === cursor.measure_id) || buildMeasureGeometry(score, boxes)[0];
  const capacity = measureCapacity(score);
  const synthetic: ScoreEvent = {
    event_id: "score-cursor",
    type: "note",
    pitch: cursor.pitch || (cursor.staff === "left_hand" ? "C3" : "C4"),
    duration: cursor.duration,
    offset: cursor.offset,
    voice: cursor.voice,
    staff: cursor.staff,
    tie: null,
    dynamic: "mf",
    articulations: [],
    selected: false
  };
  return {
    x: geometry ? offsetToX(geometry, cursor.offset, capacity) : SCORE_LEFT,
    y: geometry
      ? cursor.staff === "left_hand"
        ? geometry.y + (LEFT_STAFF_TOP - 42) + 22
        : pitchToStaffY(synthetic, geometry.y + (STAFF_TOP - 42))
      : cursor.staff === "left_hand"
        ? LEFT_STAFF_TOP + 22
        : pitchToStaffY(synthetic)
  };
}

export function pitchFromStaffY(y: number, staff: "right_hand" | "left_hand", measureTop = 42): string {
  const rightTop = measureTop + (STAFF_TOP - 42);
  const leftTop = measureTop + (LEFT_STAFF_TOP - 42);
  if (staff === "left_hand") {
    const pitches = ["C2", "D2", "E2", "F2", "G2", "A2", "B2", "C3", "D3", "E3", "F3", "G3", "A3"];
    return pitches[Math.max(0, Math.min(pitches.length - 1, Math.round((leftTop + 46 - y) / 5) + 6))];
  }
  const pitches = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "G5"];
  return pitches[Math.max(0, Math.min(pitches.length - 1, Math.round((rightTop + 40 - y) / 5) + 2))];
}

function isStrongBeat(offset: number, meter: string): boolean {
  if (meter === "6/8") return Math.abs(offset % 1.5) < 0.001;
  return Math.abs(offset % 1) < 0.001;
}

function roundGrid(value: number): number {
  return Math.round(value * 1000) / 1000;
}
