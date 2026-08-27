import { describe, expect, it } from "vitest";
import { layoutConfigForMode, readableScoreWidth, zoomPresetValue } from "../layoutConfig";
import { buildSystemLayout } from "../systemLayout";

describe("layoutConfig", () => {
  it("uses fit_width as a readable default", () => {
    const config = layoutConfigForMode("fit_width");
    expect(config.autoFitWidth).toBe(true);
    expect(readableScoreWidth(12, "fit_width")).toBe(920);
    expect(buildSystemLayout(16, "fit_width").measuresPerSystem).toBe(4);
    expect(buildSystemLayout(16, "fit_width").systems).toHaveLength(4);
  });

  it("maps zoom presets", () => {
    expect(zoomPresetValue("125%")).toBe(1.25);
    expect(zoomPresetValue("fit_width", 920, 1840)).toBe(0.5);
  });
});
