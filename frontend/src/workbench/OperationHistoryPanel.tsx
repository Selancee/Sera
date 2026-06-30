import { summarizeOperation } from "../score/operationHistory";
import type { OperationHistory } from "../score/scoreTypes";

export default function OperationHistoryPanel({ history }: { history: OperationHistory }) {
  return (
    <section className="operation-history">
      <h2>Operation History</h2>
      <div className="history-list">
        {(history.done || []).slice(-8).reverse().map((operation) => (
          <div className="history-row" key={operation.operation_id || operation.timestamp}>
            <span>{operation.source}</span>
            <strong>{summarizeOperation(operation)}</strong>
          </div>
        ))}
        {!history.done?.length && <span>No operations yet.</span>}
      </div>
    </section>
  );
}

