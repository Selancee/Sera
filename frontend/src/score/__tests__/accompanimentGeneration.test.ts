import { describe, expect, it } from "vitest";
import { accompanimentPatch, generateLeftHandAccompanimentOperations } from "../accompanimentGeneration";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("accompanimentGeneration", () => {
  it("creates left-hand accompaniment operations and patch", () => {
    const score = createEmptyScoreDocument(2);
    const operations = generateLeftHandAccompanimentOperations(score, 1, 2, "arpeggiated");
    expect(operations.length).toBeGreaterThan(0);
    expect(operations[0].target.staff).toBe("left_hand");
    expect(accompanimentPatch(score, 1, 1).patch_type).toBe("update_texture");
  });
});
