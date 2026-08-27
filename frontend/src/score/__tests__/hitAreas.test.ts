import { describe, expect, it } from "vitest";
import { buildExpandedHitAreas, hitTestWithAreas } from "../hitAreas";
import { buildFallbackLayout } from "../renderers/layoutMapping";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("hitAreas", () => {
  it("expands event hit areas and falls back to beat grid", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({
      event_id: "n1",
      type: "note",
      pitch: "C4",
      duration: "quarter",
      offset: 0,
      voice: 1,
      staff: "right_hand",
      tie: null,
      dynamic: "mf",
      articulations: [],
      selected: false
    });
    const boxes = buildFallbackLayout(score);
    const area = buildExpandedHitAreas(score, boxes)[0];
    const measureBox = boxes.find((box) => box.type === "measure");
    expect(area.width).toBeGreaterThan(26);
    expect(hitTestWithAreas(score, boxes, { x: area.centerX, y: area.centerY })?.type).toBe("event");
    expect(hitTestWithAreas(score, boxes, { x: (measureBox?.x || 0) + (measureBox?.width || 160) - 18, y: (measureBox?.y || 0) + 24 })?.hitMode).toBe("beat_grid");
  });
});
