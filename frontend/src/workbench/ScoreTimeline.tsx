import type { ScoreDocument } from "../score/scoreTypes";

export default function ScoreTimeline({ scoreDocument, selectedMeasureId, playbackMeasure, onSelectMeasure }: { scoreDocument: ScoreDocument; selectedMeasureId: string; playbackMeasure: number; onSelectMeasure: (measureId: string) => void }) {
  return (
    <div className="score-timeline">
      {scoreDocument.measures.map((measure) => (
        <button
          className={`${selectedMeasureId === measure.measure_id ? "selected" : ""} ${playbackMeasure === measure.number ? "playing" : ""}`}
          key={measure.measure_id}
          onClick={() => onSelectMeasure(measure.measure_id)}
          type="button"
        >
          {measure.number}
        </button>
      ))}
    </div>
  );
}

