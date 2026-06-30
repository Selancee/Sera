import { FallbackSvgRenderer } from "./FallbackSvgRenderer";
import { OSMDRenderer } from "./OSMDRenderer";
import { VexFlowRenderer } from "./VexFlowRenderer";
import type { BaseScoreRenderer } from "./BaseScoreRenderer";
import type { RendererMode } from "./renderTypes";

export const RENDERER_MODES: RendererMode[] = ["auto", "osmd", "vexflow", "fallback"];

export function createRenderer(mode: RendererMode): BaseScoreRenderer {
  if (mode === "osmd") return new OSMDRenderer();
  if (mode === "vexflow") return new VexFlowRenderer();
  return new FallbackSvgRenderer();
}

export function primaryRendererForMode(mode: RendererMode): RendererMode {
  return mode === "auto" ? "osmd" : mode;
}

export function rendererLabel(mode: RendererMode) {
  return {
    auto: "Auto",
    osmd: "OSMD",
    vexflow: "VexFlow",
    fallback: "Fallback SVG"
  }[mode];
}
