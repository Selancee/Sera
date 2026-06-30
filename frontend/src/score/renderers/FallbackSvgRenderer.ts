import { BaseScoreRenderer } from "./BaseScoreRenderer";
import { buildFallbackLayout } from "./layoutMapping";
import type { RenderContext, RendererResult } from "./renderTypes";

export class FallbackSvgRenderer extends BaseScoreRenderer {
  readonly mode = "fallback" as const;

  async render(container: HTMLElement, context: RenderContext): Promise<RendererResult> {
    const started = performance.now();
    container.dataset.renderer = "fallback";
    container.dataset.layoutBoxes = String(buildFallbackLayout(context.scoreDocument).length);
    return {
      requestedMode: "fallback",
      activeMode: "fallback",
      state: "ready",
      message: "SVG fallback renderer active",
      renderMs: Math.round(performance.now() - started)
    };
  }
}
