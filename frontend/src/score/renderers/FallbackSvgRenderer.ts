import { BaseScoreRenderer } from "./BaseScoreRenderer";
import { buildFallbackLayout } from "./layoutMapping";
import type { RenderContext, RendererResult } from "./renderTypes";

export class FallbackSvgRenderer extends BaseScoreRenderer {
  readonly mode = "fallback" as const;

  async render(container: HTMLElement, context: RenderContext): Promise<RendererResult> {
    const started = performance.now();
    container.dataset.renderer = "fallback";
    container.dataset.layoutBoxes = String(buildFallbackLayout(context.scoreDocument, context.layoutMode || "fit_width").length);
    container.dataset.layoutMode = context.layoutMode || "fit_width";
    return {
      requestedMode: "fallback",
      activeMode: "fallback",
      state: "ready",
      message: "SVG fallback renderer active with wrapped systems",
      renderMs: Math.round(performance.now() - started)
    };
  }
}
