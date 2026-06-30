const DURATIONS = ["whole", "half", "quarter", "eighth", "sixteenth", "dotted_quarter", "dotted_eighth", "rest"];

export default function DurationPalette({ onSelect }: { onSelect: (duration: string) => void }) {
  return (
    <section className="workbench-tool-group">
      <h3>Durations</h3>
      <div className="palette-grid duration-grid">
        {DURATIONS.map((duration) => (
          <button key={duration} onClick={() => onSelect(duration)} type="button">
            {duration.replace("_", " ")}
          </button>
        ))}
      </div>
    </section>
  );
}

