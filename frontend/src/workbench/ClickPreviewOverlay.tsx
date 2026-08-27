import type { ClickToNotatePreview } from "../score/clickToNotate";
import { buildMeasureGeometry, measureCapacity, offsetToX } from "../score/scoreGrid";
import type { LayoutBox } from "../score/renderers/renderTypes";
import { LEFT_STAFF_TOP, STAFF_TOP, pitchToStaffY } from "../score/renderers/layoutMapping";
import type { ScoreDocument, ScoreEvent } from "../score/scoreTypes";

export default function ClickPreviewOverlay({
  boxes,
  preview,
  scoreDocument,
  visible = true
}: {
  boxes: LayoutBox[];
  preview: ClickToNotatePreview | null;
  scoreDocument: ScoreDocument;
  visible?: boolean;
}) {
  if (!visible || !preview || preview.action === "select" || preview.action === "move_cursor") return null;
  const geometry = buildMeasureGeometry(scoreDocument, boxes).find((item) => item.measureId === preview.measureId);
  if (!geometry) return null;
  const x = offsetToX(geometry, preview.offset, measureCapacity(scoreDocument));
  const synthetic: ScoreEvent = {
    event_id: "click-preview",
    type: preview.action === "insert_rest" ? "rest" : "note",
    pitch: preview.pitch,
    duration: preview.duration,
    offset: preview.offset,
    voice: preview.voice,
    staff: preview.staff,
    tie: null,
    dynamic: "mf",
    articulations: [],
    selected: false
  };
  const y = preview.action === "insert_rest" ? (preview.staff === "left_hand" ? LEFT_STAFF_TOP + 22 : STAFF_TOP + 22) : pitchToStaffY(synthetic);
  const className = `click-preview-overlay ${preview.valid ? "valid" : "invalid"} ${preview.action}`;
  return (
    <g className={className} aria-label="Click notation preview">
      <line className="click-preview-beat" x1={x} x2={x} y1={geometry.y} y2={geometry.y + geometry.height} />
      {preview.action === "insert_rest" ? (
        <rect height="10" rx="2" width="18" x={x - 9} y={y - 5} />
      ) : (
        <>
          <ellipse cx={x} cy={y} rx="7" ry="5" transform={`rotate(-18 ${x} ${y})`} />
          <line x1={x + 6} x2={x + 6} y1={y} y2={y - 30} />
          {preview.dotted && <circle cx={x + 15} cy={y - 1} r="2.2" />}
        </>
      )}
      <text x={x + 12} y={Math.max(20, y - 24)}>
        {preview.action === "insert_rest" ? "rest" : preview.pitch} {preview.duration.replace("_", " ")}
      </text>
      {!preview.valid && <text className="click-preview-warning" x={x + 12} y={Math.min(212, y + 28)}>{preview.warning || "invalid"}</text>}
    </g>
  );
}
