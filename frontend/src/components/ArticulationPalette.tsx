const ARTICULATIONS = ["staccato", "tenuto", "accent", "legato"];

export default function ArticulationPalette({ onSelect }: { onSelect: (articulation: string) => void }) {
  return (
    <section className="workbench-tool-group">
      <h3>Articulations</h3>
      <div className="palette-grid duration-grid">
        {ARTICULATIONS.map((item) => (
          <button key={item} onClick={() => onSelect(item)} type="button">
            {item}
          </button>
        ))}
      </div>
    </section>
  );
}

