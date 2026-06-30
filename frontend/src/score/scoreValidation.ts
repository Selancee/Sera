import type { ScoreDocument } from "./scoreTypes";

export function validateLocalScore(scoreDocument: ScoreDocument) {
  const emptyMeasures = scoreDocument.measures.filter((measure) => measure.events.length === 0);
  return {
    valid_musicxml: emptyMeasures.length === 0,
    warnings: emptyMeasures.map((measure) => `Measure ${measure.number} has no editable events.`),
    errors: [],
    empty_measure_count: emptyMeasures.length
  };
}

