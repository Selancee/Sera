import { describe, expect, it } from "vitest";
import { computeScoreDiff } from "../scoreDiff";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("scoreDiff", () => {
  it("counts added and changed events", () => {
    const before = createEmptyScoreDocument(1);
    before.measures[0].events.push({
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
    const after = JSON.parse(JSON.stringify(before));
    after.measures[0].events[0].pitch = "D4";
    after.measures[0].events.push({ ...after.measures[0].events[0], event_id: "n2", pitch: "E4", offset: 1 });
    const diff = computeScoreDiff(before, after);
    expect(diff.pitch_changed).toBe(1);
    expect(diff.added).toBe(1);
  });
});
