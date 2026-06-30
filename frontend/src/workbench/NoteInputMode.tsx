import type { NoteDuration, NoteInputCursor } from "../score/noteInput";

type Props = {
  editMode: "select" | "note_input";
  cursor: NoteInputCursor;
  warning?: string;
  onEditMode: (mode: "select" | "note_input") => void;
  onDuration: (duration: NoteDuration) => void;
  onCursor: (cursor: NoteInputCursor) => void;
  onFillRests: () => void;
};

const DURATIONS: NoteDuration[] = ["whole", "half", "quarter", "eighth", "sixteenth", "dotted_half", "dotted_quarter", "dotted_eighth", "triplet_eighth"];

export default function NoteInputMode({ editMode, cursor, warning, onEditMode, onDuration, onCursor, onFillRests }: Props) {
  return (
    <section className="workbench-tool-group note-input-mode">
      <h3>Note Input</h3>
      <div className="segmented-row">
        <button className={editMode === "select" ? "active" : ""} onClick={() => onEditMode("select")} type="button">Select</button>
        <button className={editMode === "note_input" ? "active" : ""} onClick={() => onEditMode("note_input")} type="button">Note Input</button>
      </div>
      <div className="note-cursor-grid">
        <span>M{cursor.measureNumber}</span>
        <span>{cursor.staff === "right_hand" ? "RH" : "LH"}</span>
        <span>V{cursor.voice}</span>
        <span>@{cursor.offset}</span>
      </div>
      <div className="duration-grid compact">
        {DURATIONS.map((duration) => (
          <button className={cursor.duration === duration ? "active" : ""} key={duration} onClick={() => onDuration(duration)} type="button">
            {duration.replace("_", " ")}
          </button>
        ))}
      </div>
      <div className="inspector-grid">
        <label>
          Staff
          <select value={cursor.staff} onChange={(event) => onCursor({ ...cursor, staff: event.target.value as NoteInputCursor["staff"] })}>
            <option value="right_hand">right hand</option>
            <option value="left_hand">left hand</option>
          </select>
        </label>
        <label>
          Voice
          <select value={cursor.voice} onChange={(event) => onCursor({ ...cursor, voice: Number(event.target.value) as 1 | 2 })}>
            <option value={1}>voice 1</option>
            <option value={2}>voice 2</option>
          </select>
        </label>
        <label>
          Accidental
          <select value={cursor.accidental} onChange={(event) => onCursor({ ...cursor, accidental: event.target.value as NoteInputCursor["accidental"] })}>
            <option value="">none</option>
            <option value="sharp">sharp</option>
            <option value="flat">flat</option>
            <option value="natural">natural</option>
          </select>
        </label>
        <label>
          Octave
          <input max="7" min="1" type="number" value={cursor.octave} onChange={(event) => onCursor({ ...cursor, octave: Number(event.target.value) || 4 })} />
        </label>
      </div>
      <label className="inline-check">
        <input checked={cursor.chordMode} onChange={(event) => onCursor({ ...cursor, chordMode: event.target.checked })} type="checkbox" />
        chord tone input
      </label>
      <button onClick={onFillRests} type="button">Fill measure with rests</button>
      {warning && <p className="inline-warning">{warning}</p>}
    </section>
  );
}
