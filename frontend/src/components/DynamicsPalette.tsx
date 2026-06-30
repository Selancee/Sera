const DYNAMICS = ["p", "mp", "mf", "f", "cresc.", "dim."];

export default function DynamicsPalette({ onSelect }: { onSelect: (dynamic: string) => void }) {
  return (
    <section className="workbench-tool-group">
      <h3>Dynamics</h3>
      <div className="palette-grid">
        {DYNAMICS.map((dynamic) => (
          <button key={dynamic} onClick={() => onSelect(dynamic)} type="button">
            {dynamic}
          </button>
        ))}
      </div>
    </section>
  );
}

