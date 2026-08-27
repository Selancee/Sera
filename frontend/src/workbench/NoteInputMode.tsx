import type { NoteDuration, NoteInputCursor } from "../score/noteInput";
import { useI18n } from "../i18n/useI18n";
import { DurationGlyphLabel } from "../components/NotationGlyph";
import { formatDuration, formatMusicTerm } from "../i18n/musicTerms";

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
  const { t } = useI18n();
  return (
    <section className="workbench-tool-group note-input-mode">
      <h3>{t("workbench.noteInput")}</h3>
      <div className="segmented-row">
        <button className={editMode === "select" ? "active" : ""} onClick={() => onEditMode("select")} type="button">{t("workbench.selectMode")}</button>
        <button className={editMode === "note_input" ? "active" : ""} onClick={() => onEditMode("note_input")} type="button">{t("workbench.noteInput")}</button>
      </div>
      <div className="note-cursor-grid">
        <span>M{cursor.measureNumber}</span>
        <span>{cursor.staff === "right_hand" ? "RH" : "LH"}</span>
        <span>V{cursor.voice}</span>
        <span>@{cursor.offset}</span>
      </div>
      <div className="duration-grid compact">
        {DURATIONS.map((duration) => (
          <button aria-label={formatDuration(duration, t)} className={`duration-button ${cursor.duration === duration ? "active" : ""}`} key={duration} onClick={() => onDuration(duration)} title={formatDuration(duration, t)} type="button">
            <DurationGlyphLabel duration={duration} t={t} />
          </button>
        ))}
      </div>
      <div className="inspector-grid">
        <label>
          {t("workbench.staff")}
          <select value={cursor.staff} onChange={(event) => onCursor({ ...cursor, staff: event.target.value as NoteInputCursor["staff"] })}>
            <option value="right_hand">{t("workbench.rightHand")}</option>
            <option value="left_hand">{t("workbench.leftHand")}</option>
          </select>
        </label>
        <label>
          {t("workbench.voice")}
          <select value={cursor.voice} onChange={(event) => onCursor({ ...cursor, voice: Number(event.target.value) as 1 | 2 })}>
            <option value={1}>{t("workbench.voice1")}</option>
            <option value={2}>{t("workbench.voice2")}</option>
          </select>
        </label>
        <label>
          {t("workbench.accidental")}
          <select value={cursor.accidental} onChange={(event) => onCursor({ ...cursor, accidental: event.target.value as NoteInputCursor["accidental"] })}>
            <option value="">{t("workbench.none")}</option>
            <option value="sharp">{formatMusicTerm("sharp", t)}</option>
            <option value="flat">{formatMusicTerm("flat", t)}</option>
            <option value="natural">{formatMusicTerm("natural", t)}</option>
          </select>
        </label>
        <label>
          {t("workbench.octave")}
          <input max="7" min="1" type="number" value={cursor.octave} onChange={(event) => onCursor({ ...cursor, octave: Number(event.target.value) || 4 })} />
        </label>
      </div>
      <label className="inline-check">
        <input checked={cursor.chordMode} onChange={(event) => onCursor({ ...cursor, chordMode: event.target.checked })} type="checkbox" />
        {t("workbench.chordToneInput")}
      </label>
      <button onClick={onFillRests} type="button">{t("workbench.fillMeasureWithRests")}</button>
      {warning && <p className="inline-warning">{warning}</p>}
    </section>
  );
}
