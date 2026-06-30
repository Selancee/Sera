import type { HitTarget, LayoutBox } from "./renderTypes";

export function hitTestPoint(boxes: LayoutBox[], x: number, y: number): HitTarget | null {
  const event = [...boxes]
    .reverse()
    .find((box) => box.type === "event" && containsPoint(box, x, y));
  if (event) return toHitTarget(event);
  const nearest = nearestEvent(boxes, x, y, 18);
  if (nearest) return { ...toHitTarget(nearest), hitMode: "nearest", confidence: 0.54, fallbackReason: "No direct note box hit; selected nearest event." };
  const measure = boxes.find((box) => box.type === "measure" && containsPoint(box, x, y));
  return measure ? toHitTarget(measure) : null;
}

export function hitTestMarquee(boxes: LayoutBox[], rect: { x: number; y: number; width: number; height: number }) {
  const eventHits = boxes.filter((box) => box.type === "event" && intersects(box, rect)).map(toHitTarget);
  if (eventHits.length) return eventHits;
  return boxes.filter((box) => box.type === "measure" && intersects(box, rect)).map(toHitTarget);
}

export function containsPoint(box: LayoutBox, x: number, y: number) {
  return x >= box.x && x <= box.x + box.width && y >= box.y && y <= box.y + box.height;
}

export function intersects(a: LayoutBox, b: { x: number; y: number; width: number; height: number }) {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

function toHitTarget(box: LayoutBox): HitTarget {
  return {
    type: box.type,
    measureId: box.measureId,
    measureNumber: box.measureNumber,
    eventId: box.eventId,
    staff: box.staff,
    voice: box.voice,
    hitMode: box.hitMode,
    confidence: box.confidence,
    fallbackReason: box.fallbackReason
  };
}

function nearestEvent(boxes: LayoutBox[], x: number, y: number, maxDistance: number) {
  let best: LayoutBox | null = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const box of boxes) {
    if (box.type !== "event") continue;
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    const distance = Math.hypot(cx - x, cy - y);
    if (distance < bestDistance && distance <= maxDistance) {
      best = box;
      bestDistance = distance;
    }
  }
  return best;
}
