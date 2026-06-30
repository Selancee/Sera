import type { ScoreDocument } from "./scoreTypes";

export function measurePlaybackLabels(scoreDocument: ScoreDocument) {
  return scoreDocument.measures.map((measure) => `M${measure.number}`);
}

