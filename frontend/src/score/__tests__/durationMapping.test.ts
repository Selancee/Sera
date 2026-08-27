import { describe, expect, it } from "vitest";
import { mapDurationForInsertion, normalizeDuration } from "../durationMapping";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("durationMapping", () => {
  it("normalizes dotted duration settings", () => {
    expect(normalizeDuration("quarter", true)).toBe("dotted_quarter");
    expect(normalizeDuration("dotted_eighth", false)).toBe("dotted_eighth");
  });

  it("prevents measure overflow", () => {
    const score = createEmptyScoreDocument(1);
    const result = mapDurationForInsertion({
      score,
      measureId: "m1",
      staff: "right_hand",
      voice: 1,
      offset: 3.5,
      duration: "quarter"
    });

    expect(result.valid).toBe(false);
    expect(result.clickAction).toBe("invalid");
  });

  it("prefers replacing a covering rest", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({
      event_id: "m1_r1",
      type: "rest",
      pitch: "",
      duration: "quarter",
      offset: 1,
      voice: 1,
      staff: "right_hand",
      tie: null,
      dynamic: "mf",
      articulations: [],
      selected: false
    });
    const result = mapDurationForInsertion({
      score,
      measureId: "m1",
      staff: "right_hand",
      voice: 1,
      offset: 1,
      duration: "eighth"
    });

    expect(result.clickAction).toBe("replace_rest");
    expect(result.replaceEventId).toBe("m1_r1");
  });
});
