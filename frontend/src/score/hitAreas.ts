import { locateBeatGridPoint } from "./beatGrid";
import type { LayoutBox, HitTarget } from "./renderers/renderTypes";
import { containsPoint } from "./renderers/hitTesting";
import type { ScoreCursorSnap } from "./scoreCursor";
import type { ScoreDocument } from "./scoreTypes";

export type ExpandedHitArea = LayoutBox & {
  centerX: number;
  centerY: number;
  label: string;
};

export function buildExpandedHitAreas(score: ScoreDocument, boxes: LayoutBox[], pad = 10): ExpandedHitArea[] {
  return boxes
    .filter((box) => box.type === "event")
    .map((box) => {
      const measure = score.measures.find((item) => item.measure_id === box.measureId);
      const event = measure?.events.find((item) => item.event_id === box.eventId);
      return {
        ...box,
        x: box.x - pad,
        y: box.y - pad,
        width: box.width + pad * 2,
        height: box.height + pad * 2,
        centerX: box.x + box.width / 2,
        centerY: box.y + box.height / 2,
        label: event ? `${event.type} ${event.pitch || "rest"} ${event.duration} measure ${box.measureNumber} beat ${(Number(event.offset || 0) + 1).toFixed(2)} ${event.staff} voice ${event.voice}` : `event ${box.eventId}`
      };
    });
}

export function hitTestWithAreas(
  score: ScoreDocument,
  boxes: LayoutBox[],
  point: { x: number; y: number },
  snap: ScoreCursorSnap = "beat",
  voice = 1
): HitTarget | null {
  const direct = nearestExpandedEvent(score, boxes, point);
  if (direct) return direct;
  return locateBeatGridPoint(score, point, snap, boxes, voice);
}

export function nearestExpandedEvent(score: ScoreDocument, boxes: LayoutBox[], point: { x: number; y: number }): HitTarget | null {
  const hits = buildExpandedHitAreas(score, boxes).filter((area) => containsPoint(area, point.x, point.y));
  if (!hits.length) return null;
  hits.sort((a, b) => Math.hypot(a.centerX - point.x, a.centerY - point.y) - Math.hypot(b.centerX - point.x, b.centerY - point.y));
  const area = hits[0];
  return {
    type: "event",
    measureId: area.measureId,
    measureNumber: area.measureNumber,
    eventId: area.eventId,
    staff: area.staff,
    voice: area.voice,
    hitMode: "expanded",
    confidence: area.confidence ? Math.max(area.confidence, 0.78) : 0.78,
    fallbackReason: area.label
  };
}
