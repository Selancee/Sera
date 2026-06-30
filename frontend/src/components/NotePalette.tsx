const NOTES = ["C", "D", "E", "F", "G", "A", "B"];

export default function NotePalette({ onInsert, onTranspose }: { onInsert: (pitch: string) => void; onTranspose: (semitones: number) => void }) {
  return (
    <section className="workbench-tool-group">
      <h3>Notes</h3>
      <div className="palette-grid">
        {NOTES.map((note) => (
          <button key={note} onClick={() => onInsert(`${note}4`)} type="button">
            {note}
          </button>
        ))}
      </div>
      <div className="toolbar-row">
        <button onClick={() => onTranspose(12)} type="button">8va</button>
        <button onClick={() => onTranspose(-12)} type="button">8vb</button>
        <button onClick={() => onTranspose(1)} type="button">+1</button>
        <button onClick={() => onTranspose(-1)} type="button">-1</button>
      </div>
    </section>
  );
}

