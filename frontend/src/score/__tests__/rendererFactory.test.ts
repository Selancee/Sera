import { describe, expect, it } from "vitest";
import { createRenderer, primaryRendererForMode, RENDERER_MODES } from "../renderers/rendererFactory";

describe("rendererFactory", () => {
  it("resolves renderer modes with fallback support", () => {
    expect(RENDERER_MODES).toEqual(["auto", "osmd", "vexflow", "fallback"]);
    expect(primaryRendererForMode("auto")).toBe("osmd");
    expect(createRenderer("fallback").mode).toBe("fallback");
  });
});
