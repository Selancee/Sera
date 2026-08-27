import { locateBeatGridPoint } from "./beatGrid";
import { mapDurationForInsertion } from "./durationMapping";
import { defaultStaffLayout, mapYToPitch, type PitchResult } from "./pitchMapping";
import type { HitTarget, LayoutBox } from "./renderers/renderTypes";
import type { ScoreCursor, ScoreCursorSnap } from "./scoreCursor";
import type { ScoreDocument, ScoreOperation } from "./scoreTypes";

export type ClickInputMode = "select" | "note_input" | "rest_input";

export type ClickToNotatePreview = {
  action: "select" | "move_cursor" | "insert_note" | "insert_rest" | "replace_rest" | "invalid";
  valid: boolean;
  measureId: string;
  measureNumber: number;
  beat: number;
  offset: number;
  staff: "right_hand" | "left_hand";
  voice: 1 | 2;
  pitch: string;
  duration: string;
  dotted: boolean;
  accidentalMode: "none" | "sharp" | "flat" | "natural";
  confidence: "high" | "medium" | "low";
  warning: string;
  pitchResult: PitchResult;
  target?: HitTarget | null;
  replaceEventId?: string;
};

export function buildClickToNotatePreview(params: {
  score: ScoreDocument;
  cursor: ScoreCursor;
  hitTarget: HitTarget | null;
  point: { x: number; y: number };
  boxes?: LayoutBox[];
  snap?: ScoreCursorSnap;
  inputMode: ClickInputMode;
  duration: string;
  dotted?: boolean;
  accidentalMode?: "" | "sharp" | "flat" | "natural";
  chordTone?: boolean;
}): ClickToNotatePreview | null {
  const beatHit = locateBeatGridPoint(params.score, params.point, params.snap || params.cursor.snap, params.boxes || [], params.cursor.voice);
  const target = params.hitTarget?.measureId ? params.hitTarget : beatHit;
  if (!target?.measureId) return null;
  const measure = params.score.measures.find((item) => item.measure_id === target.measureId || item.number === target.measureNumber);
  if (!measure) return null;
  const staff = (target.staff === "left_hand" ? "left_hand" : target.staff === "right_hand" ? "right_hand" : params.cursor.staff) as "right_hand" | "left_hand";
  const voice = (target.voice === 2 ? 2 : params.cursor.voice === 2 ? 2 : 1) as 1 | 2;
  const clef = staff === "left_hand" ? "bass" : "treble";
  const pitchResult = mapYToPitch({
    y: params.point.y,
    staffId: staff,
    clef,
    keySignature: params.score.global.key,
    staffLayout: defaultStaffLayout(staff, clef),
    accidentalMode: params.accidentalMode || "none"
  });
  const offset = typeof target.offset === "number" ? target.offset : beatHit?.offset ?? params.cursor.offset;
  const beat = typeof target.beat === "number" ? target.beat : beatHit?.beat ?? offset + 1;
  if (params.inputMode === "select") {
    return {
      action: target.type === "event" ? "select" : "move_cursor",
      valid: true,
      measureId: measure.measure_id,
      measureNumber: measure.number,
      beat,
      offset,
      staff,
      voice,
      pitch: target.pitch || pitchResult.pitch,
      duration: params.duration,
      dotted: Boolean(params.dotted),
      accidentalMode: normalizeAccidental(params.accidentalMode),
      confidence: pitchResult.confidence,
      warning: "",
      pitchResult,
      target
    };
  }
  const insertingRest = params.inputMode === "rest_input";
  const duration = mapDurationForInsertion({
    score: params.score,
    measureId: measure.measure_id,
    staff,
    voice,
    offset,
    duration: params.duration,
    dotted: params.dotted,
    insertingRest
  });
  const action = duration.valid ? duration.clickAction : "invalid";
  return {
    action,
    valid: duration.valid && pitchResult.confidence !== "low",
    measureId: measure.measure_id,
    measureNumber: measure.number,
    beat,
    offset,
    staff,
    voice,
    pitch: pitchResult.pitch,
    duration: duration.duration,
    dotted: duration.dotted,
    accidentalMode: normalizeAccidental(params.accidentalMode),
    confidence: pitchResult.confidence,
    warning: duration.warning || (pitchResult.confidence === "low" ? "Pitch mapping confidence is low; cursor will move but insertion is blocked." : ""),
    pitchResult,
    target,
    replaceEventId: duration.replaceEventId
  };
}

export function createClickToNotateOperation(preview: ClickToNotatePreview, chordTone = false): ScoreOperation | null {
  if (!preview.valid || preview.action === "invalid" || preview.action === "select" || preview.action === "move_cursor") return null;
  if (preview.action === "replace_rest" && preview.replaceEventId) {
    return {
      type: "convert_rest_to_note",
      source: "user",
      target: {
        measure_id: preview.measureId,
        measure: preview.measureNumber,
        event_id: preview.replaceEventId,
        staff: preview.staff,
        voice: preview.voice,
        offset: preview.offset
      },
      after: {
        pitch: preview.pitch,
        duration: preview.duration,
        dotted: preview.dotted,
        offset: preview.offset,
        staff: preview.staff,
        voice: preview.voice,
        accidental: preview.accidentalMode === "none" ? "" : preview.accidentalMode,
        dynamic: "mf",
        chord_tone: chordTone
      },
      description: `Click replace rest with ${preview.pitch} at M${preview.measureNumber} beat ${preview.beat}`
    };
  }
  const eventIdPrefix = preview.action === "insert_rest" ? "r" : "e";
  const operationType = preview.action === "insert_rest" ? "insert_rest" : "insert_note";
  return {
    type: operationType,
    source: "user",
    target: {
      measure_id: preview.measureId,
      measure: preview.measureNumber,
      staff: preview.staff,
      voice: preview.voice,
      offset: preview.offset
    },
    after: {
      event_id: `${preview.measureId}_${eventIdPrefix}${Date.now().toString(36)}`,
      pitch: operationType === "insert_note" ? preview.pitch : "",
      duration: preview.duration,
      dotted: preview.dotted,
      offset: preview.offset,
      staff: preview.staff,
      voice: preview.voice,
      accidental: preview.accidentalMode === "none" ? "" : preview.accidentalMode,
      dynamic: "mf",
      chord_tone: chordTone
    },
    description: operationType === "insert_rest" ? `Click input rest at M${preview.measureNumber} beat ${preview.beat}` : `Click input ${preview.pitch} at M${preview.measureNumber} beat ${preview.beat}`
  };
}

function normalizeAccidental(accidental: "" | "sharp" | "flat" | "natural" | undefined): "none" | "sharp" | "flat" | "natural" {
  return accidental || "none";
}
