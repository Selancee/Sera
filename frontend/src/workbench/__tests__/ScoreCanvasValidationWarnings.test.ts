import { describe, expect, it } from "vitest";
import { validationWarningText } from "../ScoreCanvas";

describe("ScoreCanvas validation warning normalization", () => {
  it("accepts legacy strings and strict validation issue objects", () => {
    expect(validationWarningText("Measure 3: empty measure")).toBe("Measure 3: empty measure");
    expect(validationWarningText({ message: "Measure 2: protected warning" })).toBe("Measure 2: protected warning");
    expect(validationWarningText({ message: { nested: true } })).toBe("");
  });
});
