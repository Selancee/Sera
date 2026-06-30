import type { RenderContext, RendererMode, RendererResult } from "./renderTypes";

export abstract class BaseScoreRenderer {
  abstract readonly mode: RendererMode;

  abstract render(container: HTMLElement, context: RenderContext): Promise<RendererResult>;

  clear(container: HTMLElement) {
    container.innerHTML = "";
  }
}
