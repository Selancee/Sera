import { DEFAULT_STAFF_LANES } from "../score/staffLanes";
import type { LayoutBox } from "../score/renderers/renderTypes";

export default function StaffLaneOverlay({ activeStaff, boxes = [], visible = true }: { activeStaff: string; boxes?: LayoutBox[]; visible?: boolean }) {
  if (!visible) return null;
  const measureBoxes = boxes.filter((box) => box.type === "measure");
  if (measureBoxes.length) {
    return (
      <g className="staff-lane-overlay" aria-label="Staff lanes">
        {measureBoxes.map((box) => (
          <g key={box.measureId}>
            <rect className={activeStaff === "right_hand" ? "active" : ""} height="84" width={box.width} x={box.x} y={box.y} />
            <rect className={activeStaff === "left_hand" ? "active" : ""} height={Math.max(64, box.height - 84)} width={box.width} x={box.x} y={box.y + 84} />
          </g>
        ))}
      </g>
    );
  }
  return (
    <g className="staff-lane-overlay" aria-label="Staff lanes">
      {DEFAULT_STAFF_LANES.map((lane) => (
        <rect className={activeStaff === lane.staff ? "active" : ""} height={lane.y2 - lane.y1} key={lane.staff} width="100%" x="0" y={lane.y1} />
      ))}
    </g>
  );
}
