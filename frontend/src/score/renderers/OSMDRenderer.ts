import { BaseScoreRenderer } from "./BaseScoreRenderer";
import { buildOverlayHitMap } from "./layoutMapping";
import type { RenderContext, RendererResult } from "./renderTypes";

export class OSMDRenderer extends BaseScoreRenderer {
  readonly mode = "osmd" as const;

  async render(container: HTMLElement, context: RenderContext): Promise<RendererResult> {
    const started = performance.now();
    this.clear(container);
    const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
    const osmd = new OpenSheetMusicDisplay(container, {
      autoResize: true,
      drawTitle: true,
      drawingParameters: "default",
      renderSingleHorizontalStaffline: false
    });
    await osmd.load(context.musicxml);
    osmd.zoom = context.zoom;
    osmd.render();
    if (!container.querySelector("svg") && !container.textContent?.trim()) {
      throw new Error("OSMD rendered a blank score; fallback renderer is recommended.");
    }
    const hitMap = buildOverlayHitMap(context.scoreDocument, "osmd", context.layoutMode || "fit_width");
    return {
      requestedMode: "osmd",
      activeMode: "osmd",
      state: "ready",
      message: "OpenSheetMusicDisplay renderer active",
      renderMs: Math.round(performance.now() - started),
      layoutBoxes: hitMap.boxes,
      mappingDebug: hitMap.debug
    };
  }
}
