import { describe, expect, it } from "vitest";
import { createPartialPatch, patchCanAccept, previewLocalPatch } from "../scorePatches";
import { createEmptyScoreDocument, type ScorePatch } from "../scoreTypes";

describe("scorePatches", () => {
  it("previews local patch operations", () => {
    const score = createEmptyScoreDocument(2);
    const patch: ScorePatch = {
      patch_id: "p1",
      patch_type: "transform_notes",
      target_range: { start_measure: 1, end_measure: 1 },
      operations: [
        { source: "agent", type: "insert_note", target: { measure: 1 }, after: { pitch: "C4" }, description: "Insert" }
      ],
      rationale: "test",
      expected_effect: "test",
      prompt_alignment: { instruction: "", matched_aspects: [], risk_aspects: [] },
      validation_expectations: {}
    };
    const preview = previewLocalPatch(score, patch);
    expect(preview.after_score_document.measures[0].events).toHaveLength(1);
    expect(preview.diff.added).toBe(1);
  });

  it("creates partial patches and blocks invalid previews", () => {
    const patch: ScorePatch = {
      patch_id: "p1",
      patch_type: "transform_notes",
      target_range: { start_measure: 1, end_measure: 1 },
      operations: [
        { source: "agent", type: "insert_note", target: { measure: 1 }, after: { pitch: "C4" }, description: "A" },
        { source: "agent", type: "change_dynamic", target: { measure: 1 }, after: { dynamic: "p" }, description: "B" }
      ],
      rationale: "test",
      expected_effect: "test",
      prompt_alignment: { instruction: "", matched_aspects: [], risk_aspects: [] },
      validation_expectations: {}
    };
    expect(createPartialPatch(patch, [1]).operations[0].type).toBe("change_dynamic");
    expect(patchCanAccept({ patch, patch_validation_report: { valid: false, recommendation: "reject" } })).toBe(false);
  });
});
