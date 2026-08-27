import type { ScoreDocument } from "./scoreTypes";

export type ScoreRenderSource =
  | "backend_svg"
  | "backend_png"
  | "score_document"
  | "musicxml_osmd"
  | "musicxml_text"
  | "unavailable";

export type PlaybackSource = "midi_export" | "backend_note_events" | "score_document" | "unavailable";

export type ScoreSourceResolution = {
  source: ScoreRenderSource;
  scoreDocument: ScoreDocument | null;
  musicxml: string;
  backendUrl: string;
  warning: string;
  error: string;
};

export function resolveScoreRenderSource(result: any): ScoreSourceResolution {
  const scoreDocument = result?.score_document?.schema_version === "0.6" ? (result.score_document as ScoreDocument) : null;
  const musicxml = typeof result?.musicxml === "string" ? result.musicxml : "";
  const preview = result?.preview_render || result?.generation_metadata?.preview_render || {};
  const svgUrl = result?.backend_rendered_svg_url || preview.svg_url || "";
  const pngUrl = result?.backend_rendered_png_url || preview.png_url || "";
  if (svgUrl) {
    return { source: "backend_svg", scoreDocument, musicxml, backendUrl: svgUrl, warning: "", error: "" };
  }
  if (pngUrl) {
    return { source: "backend_png", scoreDocument, musicxml, backendUrl: pngUrl, warning: "", error: "" };
  }
  if (musicxml) {
    return {
      source: "musicxml_osmd",
      scoreDocument,
      musicxml,
      backendUrl: "",
      warning: preview?.success === false ? String((preview.errors || [])[0] || "Backend preview renderer unavailable; trying OSMD real MusicXML preview.") : "",
      error: ""
    };
  }
  if (scoreDocument) {
    return {
      source: "unavailable",
      scoreDocument,
      musicxml: "",
      backendUrl: "",
      warning: "ScoreDocument debug fallback is disabled for the generated score preview.",
      error: "Real MusicXML or backend notation render is required for the main preview."
    };
  }
  return {
    source: "unavailable",
    scoreDocument: null,
    musicxml: "",
    backendUrl: "",
    warning: "",
    error: result?.plan?.measures?.length ? "No authoritative score source available." : "No generated score is available."
  };
}

export function resolvePlaybackSource(result: any, scoreDocumentEventCount: number): PlaybackSource {
  if (result?.midi_url || result?.exports?.midi) return "midi_export";
  if (Array.isArray(result?.note_events) && result.note_events.length > 0) return "backend_note_events";
  if (scoreDocumentEventCount > 0) return "score_document";
  return "unavailable";
}

export function hasPlanMeasuresOnly(result: any): boolean {
  return Boolean(result?.plan?.measures?.length) && !result?.score_document && !result?.musicxml && !result?.midi_url && !result?.exports?.midi;
}
