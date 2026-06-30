import type { ScoreDocument, ScoreEvent } from "../scoreTypes";
import type { HitTarget, LayoutBox } from "./renderTypes";

export const MEASURE_WIDTH = 128;
export const STAFF_TOP = 74;
export const LEFT_STAFF_TOP = 146;
export const SCORE_LEFT = 36;

export function pitchToStaffY(event: ScoreEvent) {
  const pitch = event.pitch || "C4";
  const step = pitch[0]?.toUpperCase() || "C";
  const octave = Number(pitch.match(/\d/)?.[0] || 4);
  const stepMap: Record<string, number> = { C: 112, D: 107, E: 102, F: 97, G: 92, A: 87, B: 82 };
  return (stepMap[step] || 102) - (octave - 4) * 28;
}

export function buildFallbackLayout(scoreDocument: ScoreDocument): LayoutBox[] {
  const boxes: LayoutBox[] = [];
  scoreDocument.measures.forEach((measure, index) => {
    const measureX = index * MEASURE_WIDTH + SCORE_LEFT;
    boxes.push({
      type: "measure",
      measureId: measure.measure_id,
      measureNumber: measure.number,
      x: measureX - 4,
      y: 42,
      width: MEASURE_WIDTH - 10,
      height: 152
    });
    measure.events.forEach((event, eventIndex) => {
      const x = eventX(measureX, event, eventIndex);
      const y = event.staff === "left_hand" ? LEFT_STAFF_TOP + 22 : pitchToStaffY(event);
      boxes.push({
        type: "event",
        measureId: measure.measure_id,
        measureNumber: measure.number,
        eventId: event.event_id,
        staff: event.staff,
        voice: event.voice,
        hitMode: "fallback",
        confidence: 0.86,
        eventType: event.type,
        x: x - 13,
        y: y - 18,
        width: 26,
        height: 40
      });
    });
  });
  return boxes;
}

export function buildOverlayHitMap(scoreDocument: ScoreDocument, source: "osmd" | "fallback" = "fallback") {
  const boxes = buildFallbackLayout(scoreDocument).map((box) => ({
    ...box,
    hitMode: source === "osmd" ? ("overlay" as const) : ("fallback" as const),
    confidence: box.type === "event" ? (source === "osmd" ? 0.74 : 0.86) : 0.92,
    fallbackReason: source === "osmd" ? "OSMD visual note mapping uses Sera overlay boxes when SVG internals are unavailable." : ""
  }));
  const eventBoxCount = boxes.filter((box) => box.type === "event").length;
  const measureBoxCount = boxes.filter((box) => box.type === "measure").length;
  return {
    boxes,
    debug: {
      mode: source === "osmd" ? "overlay" : "fallback",
      confidence: eventBoxCount ? (source === "osmd" ? 0.74 : 0.86) : 0.5,
      fallbackReason: source === "osmd" ? "Precise OSMD notehead ids are not stable; using deterministic ScoreDocument overlay hit map." : "",
      eventBoxCount,
      measureBoxCount
    }
  };
}

export function hitTargetFromEvent(scoreDocument: ScoreDocument, eventId: string): HitTarget | null {
  for (const measure of scoreDocument.measures) {
    const event = measure.events.find((item) => item.event_id === eventId);
    if (event) {
      return {
        type: "event",
        measureId: measure.measure_id,
        measureNumber: measure.number,
        eventId,
        staff: event.staff,
        voice: event.voice,
        hitMode: "fallback",
        confidence: 1
      };
    }
  }
  return null;
}

export function eventX(measureX: number, event: ScoreEvent, index: number) {
  return measureX + 22 + Math.max(0, Number(event.offset || index)) * 22;
}
