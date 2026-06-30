import type { OperationHistory, ScoreDocument } from "../score/scoreTypes";

export default function ScoreStatusBar({ scoreDocument, history, status, rendererStatus }: { scoreDocument: ScoreDocument; history: OperationHistory; status: string; rendererStatus?: string }) {
  return (
    <div className="score-status-bar">
      <span>{status}</span>
      {rendererStatus && <span>{rendererStatus}</span>}
      <span>{scoreDocument.measures.length} measures</span>
      <span>{history.done.length} operations</span>
      <span>{scoreDocument.global.key}</span>
      <span>{scoreDocument.global.meter}</span>
      <span>{scoreDocument.global.tempo} bpm</span>
    </div>
  );
}
