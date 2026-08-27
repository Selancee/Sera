import { describe, expect, it } from "vitest";
import { buildSystemLayout } from "../systemLayout";

describe("systemLayout", () => {
  it("wraps 16 measures into four readable systems", () => {
    const layout = buildSystemLayout(16, "fit_width");
    expect(layout.measuresPerSystem).toBe(4);
    expect(layout.systems).toHaveLength(4);
    expect(layout.measures[4].systemIndex).toBe(1);
    expect(layout.measures[4].y).toBeGreaterThan(layout.measures[0].y);
  });
});
