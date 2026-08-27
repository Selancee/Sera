import type { ScoreCursor } from "../score/scoreCursor";
import { cursorToPoint } from "../score/scoreGrid";
import type { LayoutBox } from "../score/renderers/renderTypes";
import type { ScoreDocument } from "../score/scoreTypes";

export default function ScoreCursorOverlay({ boxes = [], cursor, scoreDocument }: { boxes?: LayoutBox[]; cursor: ScoreCursor; scoreDocument: ScoreDocument }) {
  const point = cursorToPoint(scoreDocument, cursor, boxes);
  return (
    <g className={`score-cursor-overlay ${cursor.valid ? "valid" : "invalid"}`} aria-label="Score cursor">
      <line x1={point.x} x2={point.x} y1={point.y - 30} y2={point.y + 30} />
      <circle cx={point.x} cy={point.y} r="5" />
      <text x={point.x + 8} y={point.y - 12}>
        M{cursor.measure_number} B{cursor.beat.toFixed(2)} {cursor.staff === "left_hand" ? "LH" : "RH"} V{cursor.voice}
      </text>
    </g>
  );
}
