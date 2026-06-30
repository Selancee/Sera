import type { ScoreDocument, ScoreEvent, ScorePatch } from "./scoreTypes";

export type ScoreDiffSummary = {
  target_range: { start_measure: number; end_measure: number };
  operation_count: number;
  added: number;
  removed: number;
  changed: number;
  pitch_changed: number;
  duration_changed: number;
  dynamic_changed: number;
  harmony_changed: number;
  cadence_changed: number;
  changed_measures: number[];
};

export function computeScoreDiff(before: ScoreDocument, after: ScoreDocument, patch?: ScorePatch): ScoreDiffSummary {
  const target = patch?.target_range || {
    start_measure: 1,
    end_measure: Math.max(before.measures.length, after.measures.length)
  };
  const beforeMeasures = rangeMeasures(before, target.start_measure, target.end_measure);
  const afterMeasures = rangeMeasures(after, target.start_measure, target.end_measure);
  const changedMeasures = new Set<number>();
  let added = 0;
  let removed = 0;
  let changed = 0;
  let pitchChanged = 0;
  let durationChanged = 0;
  let dynamicChanged = 0;
  let harmonyChanged = 0;
  let cadenceChanged = 0;

  for (const afterMeasure of afterMeasures) {
    const beforeMeasure = beforeMeasures.find((measure) => measure.number === afterMeasure.number);
    if (!beforeMeasure) {
      added += afterMeasure.events.length;
      changedMeasures.add(afterMeasure.number);
      continue;
    }
    if (beforeMeasure.harmony !== afterMeasure.harmony) {
      harmonyChanged += 1;
      changedMeasures.add(afterMeasure.number);
    }
    if (beforeMeasure.cadence !== afterMeasure.cadence) {
      cadenceChanged += 1;
      changedMeasures.add(afterMeasure.number);
    }
    const beforeEvents = byId(beforeMeasure.events);
    const afterEvents = byId(afterMeasure.events);
    for (const [eventId, event] of afterEvents) {
      const previous = beforeEvents.get(eventId);
      if (!previous) {
        added += 1;
        changedMeasures.add(afterMeasure.number);
        continue;
      }
      const eventChanged = previous.pitch !== event.pitch || previous.duration !== event.duration || previous.dynamic !== event.dynamic || previous.offset !== event.offset;
      if (eventChanged) {
        changed += 1;
        changedMeasures.add(afterMeasure.number);
      }
      if (previous.pitch !== event.pitch) pitchChanged += 1;
      if (previous.duration !== event.duration) durationChanged += 1;
      if (previous.dynamic !== event.dynamic) dynamicChanged += 1;
    }
    for (const eventId of beforeEvents.keys()) {
      if (!afterEvents.has(eventId)) {
        removed += 1;
        changedMeasures.add(afterMeasure.number);
      }
    }
  }

  return {
    target_range: target,
    operation_count: patch?.operations?.length || 0,
    added,
    removed,
    changed,
    pitch_changed: pitchChanged,
    duration_changed: durationChanged,
    dynamic_changed: dynamicChanged,
    harmony_changed: harmonyChanged,
    cadence_changed: cadenceChanged,
    changed_measures: Array.from(changedMeasures).sort((a, b) => a - b)
  };
}

function rangeMeasures(score: ScoreDocument, start: number, end: number) {
  return score.measures.filter((measure) => measure.number >= start && measure.number <= end);
}

function byId(events: ScoreEvent[]) {
  return new Map(events.map((event) => [event.event_id, event]));
}
