import type { LayoutBox, HitTarget } from "./renderers/renderTypes";
import type { ScoreDocument } from "./scoreTypes";
import type { ScoreCursor, ScoreCursorSnap } from "./scoreCursor";
import { beatFromOffset, buildBeatGrid, geometryAtPoint, measureCapacity, offsetFromX, snapOffset } from "./scoreGrid";
import { staffAndPitchFromPoint } from "./staffLanes";

export type BeatGridHit = HitTarget & {
  beat: number;
  offset: number;
  pitch: string;
  staff: "right_hand" | "left_hand";
  voice: number;
};

export function locateBeatGridPoint(
  score: ScoreDocument,
  point: { x: number; y: number },
  snap: ScoreCursorSnap = "beat",
  boxes: LayoutBox[] = [],
  voice = 1
): BeatGridHit | null {
  const geometry = geometryAtPoint(score, point, boxes);
  if (!geometry) return null;
  const meter = String(score.global?.meter || "4/4");
  const offset = Math.min(measureCapacity(score), snapOffset(offsetFromX(geometry, point.x, measureCapacity(score)), meter, snap));
  const staffPitch = staffAndPitchFromPoint(point, geometry.y);
  return {
    type: "measure",
    measureId: geometry.measureId,
    measureNumber: geometry.measureNumber,
    staff: staffPitch.staff,
    voice,
    hitMode: "beat_grid",
    confidence: 0.68,
    fallbackReason: "No event hit; cursor snapped to the nearest beat grid point.",
    beat: beatFromOffset(offset, meter),
    offset,
    pitch: staffPitch.pitch
  };
}

export function scoreCursorFromBeatGridHit(cursor: ScoreCursor, hit: BeatGridHit): ScoreCursor {
  return {
    ...cursor,
    measure_id: hit.measureId,
    measure_number: hit.measureNumber,
    staff: hit.staff,
    voice: hit.voice === 2 ? 2 : 1,
    beat: hit.beat,
    offset: hit.offset,
    pitch: hit.pitch,
    valid: true,
    warning: ""
  };
}

export { buildBeatGrid };
