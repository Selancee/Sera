import { BaseScoreRenderer } from "./BaseScoreRenderer";
import type { RenderContext, RendererResult } from "./renderTypes";

export class VexFlowRenderer extends BaseScoreRenderer {
  readonly mode = "vexflow" as const;

  async render(container: HTMLElement, context: RenderContext): Promise<RendererResult> {
    const started = performance.now();
    this.clear(container);
    // VexFlow is reserved for a later native event-graph engraver. V0.7 keeps
    // this adapter explicit so rendererMode=vexflow degrades predictably.
    await import("vexflow");
    container.dataset.renderer = "vexflow-placeholder";
    container.dataset.measureCount = String(context.scoreDocument.measures.length);
    return {
      requestedMode: "vexflow",
      activeMode: "fallback",
      state: "fallback",
      message: "VexFlow adapter placeholder; using SVG fallback",
      renderMs: Math.round(performance.now() - started)
    };
  }
}
