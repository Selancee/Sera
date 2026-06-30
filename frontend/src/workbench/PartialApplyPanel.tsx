import type { ScoreOperation } from "../score/scoreTypes";

export default function PartialApplyPanel({
  operations,
  selectedIndexes,
  onToggle,
  onApplySelected,
  onApplyFilter
}: {
  operations: ScoreOperation[];
  selectedIndexes: number[];
  onToggle: (index: number) => void;
  onApplySelected: () => void;
  onApplyFilter: (filter: string) => void;
}) {
  if (!operations.length) return <span>No operations to partially apply.</span>;
  return (
    <div className="partial-apply">
      <div className="toolbar-row">
        <button disabled={!selectedIndexes.length} onClick={onApplySelected} type="button">Apply selected operations</button>
        <button onClick={() => onApplyFilter("measures")} type="button">Only measures</button>
        <button onClick={() => onApplyFilter("notes")} type="button">Only notes</button>
        <button onClick={() => onApplyFilter("harmony")} type="button">Only harmony</button>
        <button onClick={() => onApplyFilter("dynamics")} type="button">Only dynamics</button>
      </div>
      <div className="operation-checklist">
        {operations.map((operation, index) => (
          <label key={operation.operation_id || `${operation.type}_${index}`}>
            <input checked={selectedIndexes.includes(index)} onChange={() => onToggle(index)} type="checkbox" />
            <span>{operation.type}</span>
            <small>{operation.description}</small>
          </label>
        ))}
      </div>
    </div>
  );
}
