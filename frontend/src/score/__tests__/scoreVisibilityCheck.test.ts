import { describe, expect, it } from "vitest";
import { checkScoreVisibility } from "../scoreVisibilityCheck";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("scoreVisibilityCheck", () => {
  it("detects missing note elements", () => {
    const score = createEmptyScoreDocument(16);
    const report = checkScoreVisibility(score, "fit_width");

    expect(report.checks.measures_per_system_ok).toBe(true);
    expect(report.valid).toBe(false);
    expect(report.warnings).toContain("has_note_elements");
  });
});
