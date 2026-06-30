import { describe, expect, it } from "vitest";
import { changeSelectionVoice, duplicateMelodyToStaff, moveSelectionToStaff } from "../multiVoice";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("multiVoice", () => {
  it("creates staff and voice operations", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({ event_id: "n1", type: "note", pitch: "C4", duration: "quarter", offset: 0, voice: 1, staff: "right_hand", tie: null, dynamic: "mf", articulations: [], selected: false });
    expect(moveSelectionToStaff(score, ["n1"], "left_hand")[0].type).toBe("update_staff");
    expect(changeSelectionVoice(score, ["n1"], 2)[0].after.voice).toBe(2);
    expect(duplicateMelodyToStaff(score, "right_hand", "left_hand", 1, 1)).toHaveLength(1);
  });
});
