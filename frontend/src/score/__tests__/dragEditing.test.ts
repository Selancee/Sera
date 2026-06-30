import { describe, expect, it } from "vitest";
import { buildDragOperations, createDragPreview, transposePitch } from "../dragEditing";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("dragEditing", () => {
  it("builds pitch operations from vertical drag", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({ event_id: "n1", type: "note", pitch: "C4", duration: "quarter", offset: 0, voice: 1, staff: "right_hand", tie: null, dynamic: "mf", articulations: [], selected: false });
    const preview = createDragPreview(score, ["n1"], -16, 0);
    expect(preview.semitones).toBe(2);
    const operations = buildDragOperations(score, ["n1"], -16, 0);
    expect(operations[0].type).toBe("update_pitch");
    expect(transposePitch("C4", 2)).toBe("D4");
  });
});
