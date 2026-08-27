import { buildBeatGrid } from "../score/beatGrid";
import type { ScoreCursorSnap } from "../score/scoreCursor";
import type { LayoutBox } from "../score/renderers/renderTypes";
import type { ScoreDocument } from "../score/scoreTypes";

export default function BeatGridOverlay({ boxes = [], scoreDocument, snap = "beat", visible = false }: { boxes?: LayoutBox[]; scoreDocument: ScoreDocument; snap?: ScoreCursorSnap; visible?: boolean }) {
  if (!visible) return null;
  const points = buildBeatGrid(scoreDocument, snap, boxes);
  return (
    <g className="beat-grid-overlay" aria-label="Beat grid">
      {points.map((point) => (
        <line
          className={point.strong ? "strong" : ""}
          key={`${point.measureId}-${point.offset}`}
          x1={point.x}
          x2={point.x}
          y1={measureBoxFor(point.measureId, boxes)?.y ?? 42}
          y2={(measureBoxFor(point.measureId, boxes)?.y ?? 42) + (measureBoxFor(point.measureId, boxes)?.height ?? 176)}
        />
      ))}
    </g>
  );
}

function measureBoxFor(measureId: string, boxes: LayoutBox[]) {
  return boxes.find((box) => box.type === "measure" && box.measureId === measureId);
}
