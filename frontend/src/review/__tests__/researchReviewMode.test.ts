import { describe, expect, it } from "vitest";

import { researchReviewEnabled } from "../researchReviewMode";


describe("research review mode", () => {
  it("is hidden unless explicitly enabled for a research build", () => {
    expect(researchReviewEnabled(undefined)).toBe(false);
    expect(researchReviewEnabled("false")).toBe(false);
    expect(researchReviewEnabled("true")).toBe(true);
    expect(researchReviewEnabled(" TRUE ")).toBe(true);
  });
});
