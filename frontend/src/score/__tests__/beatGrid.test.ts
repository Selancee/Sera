import { describe, expect, it } from "vitest";
import { locateBeatGridPoint } from "../beatGrid";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("beatGrid", () => {
  it("maps empty measure clicks to the nearest snapped beat", () => {
    const score = createEmptyScoreDocument(1);
    const hit = locateBeatGridPoint(score, { x: 94, y: 88 }, "eighth");
    expect(hit?.measureNumber).toBe(1);
    expect(hit?.hitMode).toBe("beat_grid");
    expect(hit?.offset).toBeGreaterThanOrEqual(0);
    expect(hit?.staff).toBe("right_hand");
  });
});
