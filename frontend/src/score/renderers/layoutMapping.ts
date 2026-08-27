import type { ScoreDocument, ScoreEvent } from "../scoreTypes";
import { buildSystemLayout } from "../systemLayout";
import type { ScoreLayoutMode } from "../layoutConfig";
import type { HitTarget, LayoutBox } from "./renderTypes";

export const MEASURE_WIDTH = 160;
export const STAFF_TOP = 74;
export const LEFT_STAFF_TOP = 170;
export const SCORE_LEFT = 36;

export function pitchToStaffY(event: ScoreEvent, staffTop = STAFF_TOP) {
  const pitch = event.pitch || "C4";
  const step = pitch[0]?.toUpperCase() || "C";
  const octave = Number(pitch.match(/\d/)?.[0] || 4);
  const stepMap: Record<string, number> = { C: 112, D: 107, E: 102, F: 97, G: 92, A: 87, B: 82 };
  return staffTop + ((stepMap[step] || 102) - STAFF_TOP) - (octave - 4) * 28;
}

export function buildFallbackLayout(scoreDocument: ScoreDocument, mode: ScoreLayoutMode = "fit_width"): LayoutBox[] {
  const boxes: LayoutBox[] = [];
  const layout = buildSystemLayout(scoreDocument.measures.length, mode);
  scoreDocument.measures.forEach((measure, index) => {
    const measureLayout = layout.measures[index];
    const measureX = measureLayout.x;
    boxes.push({
      type: "measure",
      measureId: measure.measure_id,
      measureNumber: measure.number,
      x: measureX,
      y: measureLayout.y + 42,
      width: measureLayout.width,
      height: 176
    });
    measure.events.forEach((event, eventIndex) => {
      const x = eventX(measureX, event, eventIndex);
      const y = event.staff === "left_hand" ? measureLayout.leftStaffTop + 22 : pitchToStaffY(event, measureLayout.rightStaffTop);
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

export function buildOverlayHitMap(scoreDocument: ScoreDocument, source: "osmd" | "fallback" = "fallback", mode: ScoreLayoutMode = "fit_width") {
  const boxes = buildFallbackLayout(scoreDocument, mode).map((box) => ({
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
  return measureX + 30 + Math.max(0, Number(event.offset || index)) * 28;
}
