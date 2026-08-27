import { buildExpandedHitAreas } from "../score/hitAreas";
import type { HitTarget, LayoutBox } from "../score/renderers/renderTypes";
import type { ScoreDocument } from "../score/scoreTypes";

export default function HitAreaOverlay({ boxes = [], hoverTarget, scoreDocument, visible = false }: { boxes?: LayoutBox[]; hoverTarget?: HitTarget | null; scoreDocument: ScoreDocument; visible?: boolean }) {
  const areas = buildExpandedHitAreas(scoreDocument, boxes);
  if (!visible && !hoverTarget?.eventId) return null;
  return (
    <g className="hit-area-overlay" aria-label="Hit areas">
      {visible &&
        areas.map((area) => (
          <rect height={area.height} key={`${area.measureId}-${area.eventId}`} width={area.width} x={area.x} y={area.y}>
            <title>{area.label}</title>
          </rect>
        ))}
      {hoverTarget?.eventId &&
        areas
          .filter((area) => area.eventId === hoverTarget.eventId)
          .map((area) => <rect className="hover-target" height={area.height} key={`hover-${area.eventId}`} width={area.width} x={area.x} y={area.y} />)}
    </g>
  );
}
