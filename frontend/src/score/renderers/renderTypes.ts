import type { ScoreDocument } from "../scoreTypes";

export type RendererMode = "auto" | "osmd" | "vexflow" | "fallback";
export type RendererState = "idle" | "loading" | "ready" | "fallback" | "error";

export type RendererStatus = {
  requestedMode: RendererMode;
  activeMode: RendererMode;
  state: RendererState;
  message: string;
  renderMs: number;
};

export type HitTarget = {
  type: "measure" | "event" | "staff";
  measureId: string;
  measureNumber: number;
  eventId?: string;
  staff?: string;
  voice?: number;
  hitMode?: "osmd" | "overlay" | "fallback" | "nearest";
  confidence?: number;
  fallbackReason?: string;
};

export type LayoutBox = HitTarget & {
  x: number;
  y: number;
  width: number;
  height: number;
  eventType?: "note" | "rest" | "chord";
};

export type RenderContext = {
  scoreDocument: ScoreDocument;
  musicxml: string;
  zoom: number;
};

export type RendererResult = RendererStatus & {
  error?: string;
  layoutBoxes?: LayoutBox[];
  mappingDebug?: {
    mode: string;
    confidence: number;
    fallbackReason?: string;
    eventBoxCount: number;
    measureBoxCount: number;
  };
};
