import { describe, expect, it } from "vitest";
import { DEFAULT_LAYOUT_CONFIG } from "../layoutConfig";
import { buildSystemLayout, SYSTEM_LEFT_STAFF_TOP, SYSTEM_RIGHT_STAFF_TOP } from "../systemLayout";

describe("V0.93 readable system layout", () => {
  it("keeps 16 measures wrapped instead of one compressed row", () => {
    const layout = buildSystemLayout(16, "fit_width");

    expect(layout.systems.length).toBeGreaterThanOrEqual(4);
    expect(layout.measuresPerSystem).toBeLessThanOrEqual(DEFAULT_LAYOUT_CONFIG.maxMeasuresPerSystem);
    expect(SYSTEM_LEFT_STAFF_TOP - SYSTEM_RIGHT_STAFF_TOP).toBeGreaterThanOrEqual(DEFAULT_LAYOUT_CONFIG.grandStaffSpacing);
    expect(layout.measures[15].systemIndex).toBeGreaterThan(0);
  });
});
