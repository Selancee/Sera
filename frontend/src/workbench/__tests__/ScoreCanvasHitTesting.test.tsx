import { describe, expect, it } from "vitest";
import { hitTestPoint } from "../../score/renderers/hitTesting";
import { buildOverlayHitMap } from "../../score/renderers/layoutMapping";
import { createEmptyScoreDocument } from "../../score/scoreTypes";

describe("ScoreCanvasHitTesting", () => {
  it("hit-tests event boxes before measures", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({ event_id: "n1", type: "note", pitch: "C4", duration: "quarter", offset: 0, voice: 1, staff: "right_hand", tie: null, dynamic: "mf", articulations: [], selected: false });
    const map = buildOverlayHitMap(score, "fallback");
    const eventBox = map.boxes.find((box) => box.type === "event")!;
    expect(hitTestPoint(map.boxes, eventBox.x + 2, eventBox.y + 2)?.eventId).toBe("n1");
  });
});
