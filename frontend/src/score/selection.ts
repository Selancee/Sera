import type { HitTarget } from "./renderers/renderTypes";
import type { ScoreDocument } from "./scoreTypes";

export type ScoreSelection = {
  measureIds: string[];
  eventIds: string[];
  anchorMeasureId: string;
};

export const EMPTY_SELECTION: ScoreSelection = { measureIds: [], eventIds: [], anchorMeasureId: "" };

export function selectMeasure(selection: ScoreSelection, measureId: string, additive = false): ScoreSelection {
  if (!additive) {
    return { measureIds: [measureId], eventIds: [], anchorMeasureId: measureId };
  }
  const measureIds = toggle(selection.measureIds, measureId);
  return { measureIds, eventIds: selection.eventIds, anchorMeasureId: selection.anchorMeasureId || measureId };
}

export function selectEvent(selection: ScoreSelection, eventId: string, measureId: string, additive = false): ScoreSelection {
  if (!additive) {
    return { measureIds: [measureId], eventIds: [eventId], anchorMeasureId: measureId };
  }
  return {
    measureIds: selection.measureIds.includes(measureId) ? selection.measureIds : [...selection.measureIds, measureId],
    eventIds: toggle(selection.eventIds, eventId),
    anchorMeasureId: selection.anchorMeasureId || measureId
  };
}

export function selectMeasureRange(scoreDocument: ScoreDocument, anchorMeasureId: string, targetMeasureId: string): ScoreSelection {
  const measures = scoreDocument.measures;
  const anchorIndex = Math.max(0, measures.findIndex((measure) => measure.measure_id === anchorMeasureId));
  const targetIndex = Math.max(0, measures.findIndex((measure) => measure.measure_id === targetMeasureId));
  const start = Math.min(anchorIndex, targetIndex);
  const end = Math.max(anchorIndex, targetIndex);
  const measureIds = measures.slice(start, end + 1).map((measure) => measure.measure_id);
  return { measureIds, eventIds: [], anchorMeasureId: anchorMeasureId || targetMeasureId };
}

export function selectAllMeasures(scoreDocument: ScoreDocument): ScoreSelection {
  return {
    measureIds: scoreDocument.measures.map((measure) => measure.measure_id),
    eventIds: [],
    anchorMeasureId: scoreDocument.measures[0]?.measure_id || ""
  };
}

export function clearSelection(): ScoreSelection {
  return EMPTY_SELECTION;
}

export function selectTargets(targets: HitTarget[]): ScoreSelection {
  const measureIds = unique(targets.map((target) => target.measureId).filter(Boolean));
  const eventIds = unique(targets.filter((target) => target.type === "event" && target.eventId).map((target) => String(target.eventId)));
  return { measureIds, eventIds, anchorMeasureId: measureIds[0] || "" };
}

export function selectedEvents(scoreDocument: ScoreDocument, selection: ScoreSelection) {
  const wanted = new Set(selection.eventIds);
  return scoreDocument.measures.flatMap((measure) =>
    measure.events.filter((event) => wanted.has(event.event_id)).map((event) => ({ measure, event }))
  );
}

export function selectionSummary(scoreDocument: ScoreDocument, selection: ScoreSelection) {
  const events = selectedEvents(scoreDocument, selection);
  const measures = scoreDocument.measures.filter((measure) => selection.measureIds.includes(measure.measure_id));
  return {
    measure_count: measures.length,
    event_count: events.length,
    note_count: events.filter(({ event }) => event.type === "note").length,
    rest_count: events.filter(({ event }) => event.type === "rest").length,
    staves: unique(events.map(({ event }) => event.staff)),
    voices: unique(events.map(({ event }) => String(event.voice))),
    event_ids: events.map(({ event }) => event.event_id),
    measure_ids: measures.map((measure) => measure.measure_id)
  };
}

export function selectionToRange(scoreDocument: ScoreDocument, selection: ScoreSelection) {
  const selected = scoreDocument.measures.filter((measure) => selection.measureIds.includes(measure.measure_id));
  if (!selected.length) {
    const first = scoreDocument.measures[0];
    return { start_measure: first?.number || 1, end_measure: first?.number || 1, part_id: "piano", staff: "right_hand" };
  }
  const numbers = selected.map((measure) => measure.number);
  return { start_measure: Math.min(...numbers), end_measure: Math.max(...numbers), part_id: "piano", staff: "right_hand" };
}

function toggle(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function unique(values: string[]) {
  return Array.from(new Set(values));
}
