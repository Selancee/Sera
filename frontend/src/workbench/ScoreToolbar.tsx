import type { NoteDuration } from "../score/noteInput";
import type { ScoreLayoutMode } from "../score/layoutConfig";
import { useI18n } from "../i18n/useI18n";
import { DurationGlyphLabel, NotationGlyph } from "../components/NotationGlyph";
import { formatDuration, formatMusicTerm } from "../i18n/musicTerms";

type Props = {
  tool: string;
  zoom: number;
  rendererMode: string;
  layoutMode: ScoreLayoutMode;
  editMode: "select" | "note_input";
  duration: NoteDuration;
  dotted: boolean;
  accidental: string;
  staff: string;
  voice: number;
  loop: boolean;
  canUndo: boolean;
  canRedo: boolean;
  onTool: (tool: string) => void;
  onEditMode: (mode: "select" | "note_input") => void;
  onDuration: (duration: NoteDuration) => void;
  onDotted: () => void;
  onAccidental: (accidental: string) => void;
  onStaff: (staff: "right_hand" | "left_hand") => void;
  onVoice: (voice: 1 | 2) => void;
  onRendererMode: (mode: string) => void;
  onLayoutMode: (mode: ScoreLayoutMode) => void;
  onUndo: () => void;
  onRedo: () => void;
  onNew: () => void;
  onImport: (file: File) => void;
  onSave: () => void;
  onOpen: (file: File) => void;
  onExportMusicXml: () => void;
  onExportMidi: () => void;
  onExportPdf: () => void;
  onPlay: () => void;
  onStop: () => void;
  onLoop: (loop: boolean) => void;
  onZoom: (zoom: number) => void;
  onFitWidth: () => void;
  onResetView: () => void;
  onRerender: () => void;
  onOpenMusicXmlTextPreview: () => void;
  onTie: () => void;
  onSlur: () => void;
};

const DURATIONS: NoteDuration[] = ["whole", "half", "quarter", "eighth", "sixteenth", "dotted_half", "dotted_quarter", "dotted_eighth", "triplet_eighth"];
const ACCIDENTAL_SYMBOLS: Record<string, string> = { sharp: "♯", flat: "♭", natural: "♮" };

export default function ScoreToolbar(props: Props) {
  const { t } = useI18n();
  return (
    <div className="workbench-toolbar notation-toolbar">
      <div className="toolbar-row">
        <strong>{t("workbench.title")}</strong>
        <button className={props.editMode === "select" ? "active" : ""} onClick={() => props.onEditMode("select")} type="button">{t("workbench.selectMode")}</button>
        <button className={props.editMode === "note_input" ? "active" : ""} onClick={() => props.onEditMode("note_input")} type="button">{t("workbench.noteInput")}</button>
        {["note", "rest", "delete"].map((tool) => (
          <button aria-label={t(`workbench.tool.${tool}`)} className={`icon-tool-button ${props.tool === tool ? "active" : ""}`} key={tool} onClick={() => props.onTool(tool)} title={t(`workbench.tool.${tool}`)} type="button">
            {tool === "note" && <NotationGlyph duration="quarter" label={t("workbench.tool.note")} size={28} />}
            {tool === "rest" && <NotationGlyph duration="rest" kind="rest" label={t("workbench.tool.rest")} size={28} />}
            {tool === "delete" && <span aria-hidden="true" className="delete-glyph">×</span>}
            <span className="sr-only">{t(`workbench.tool.${tool}`)}</span>
          </button>
        ))}
      </div>
      <div className="toolbar-row">
        {DURATIONS.map((duration) => (
          <button aria-label={formatDuration(duration, t)} className={`duration-button ${props.duration === duration ? "active" : ""}`} key={duration} onClick={() => props.onDuration(duration)} title={formatDuration(duration, t)} type="button">
            <DurationGlyphLabel duration={duration} t={t} />
          </button>
        ))}
        <button className={props.dotted ? "active" : ""} onClick={props.onDotted} type="button">{t("workbench.dot")}</button>
        {["", "sharp", "flat", "natural"].map((accidental) => (
          <button aria-label={accidental ? formatMusicTerm(accidental, t) : t("workbench.naturalOff")} className={`accidental-button ${props.accidental === accidental ? "active" : ""}`} key={accidental || "none"} onClick={() => props.onAccidental(accidental)} title={accidental ? formatMusicTerm(accidental, t) : t("workbench.naturalOff")} type="button">
            {accidental ? ACCIDENTAL_SYMBOLS[accidental] : "—"}
          </button>
        ))}
        <button onClick={props.onTie} type="button">{t("workbench.tie")}</button>
        <button onClick={props.onSlur} type="button">{t("workbench.slur")}</button>
      </div>
      <div className="toolbar-row">
        <label>
          {t("workbench.staff")}
          <select value={props.staff} onChange={(event) => props.onStaff(event.target.value as "right_hand" | "left_hand")}>
            <option value="right_hand">{t("workbench.rightHand")}</option>
            <option value="left_hand">{t("workbench.leftHand")}</option>
          </select>
        </label>
        <label>
          {t("workbench.voice")}
          <select value={props.voice} onChange={(event) => props.onVoice(Number(event.target.value) as 1 | 2)}>
            <option value={1}>{t("workbench.voice1")}</option>
            <option value={2}>{t("workbench.voice2")}</option>
          </select>
        </label>
        <button disabled={!props.canUndo} onClick={props.onUndo} type="button">{t("workbench.undo")}</button>
        <button disabled={!props.canRedo} onClick={props.onRedo} type="button">{t("workbench.redo")}</button>
        <button onClick={props.onPlay} type="button">{t("workbench.play")}</button>
        <button onClick={props.onStop} type="button">{t("workbench.stop")}</button>
        <button className={props.loop ? "active" : ""} onClick={() => props.onLoop(!props.loop)} type="button">{t("workbench.loop")}</button>
      </div>
      <div className="toolbar-row">
        <button onClick={props.onNew} type="button">{t("workbench.new")}</button>
        <label className="file-button">
          {t("workbench.import")}
          <input accept=".musicxml,.xml,.mxl" onChange={(event) => event.target.files?.[0] && props.onImport(event.target.files[0])} type="file" />
        </label>
        <label className="file-button">
          {t("workbench.open")}
          <input accept=".json,.sera.json" onChange={(event) => event.target.files?.[0] && props.onOpen(event.target.files[0])} type="file" />
        </label>
        <button onClick={props.onSave} type="button">{t("workbench.save")}</button>
        <button onClick={props.onExportMusicXml} type="button">{t("workbench.musicxml")}</button>
        <button onClick={props.onExportMidi} type="button">{t("workbench.midi")}</button>
        <button onClick={props.onExportPdf} type="button">{t("workbench.pdf")}</button>
        <label>
          {t("workbench.zoom")}
          <input max="1.8" min="0.7" onChange={(event) => props.onZoom(Number(event.target.value))} step="0.1" type="range" value={props.zoom} />
        </label>
        <select aria-label={t("workbench.zoomPreset")} onChange={(event) => props.onZoom(Number(event.target.value))} value={String(props.zoom)}>
          <option value="0.75">75%</option>
          <option value="1">100%</option>
          <option value="1.25">125%</option>
          <option value="1.5">150%</option>
        </select>
        <button onClick={props.onFitWidth} type="button">{t("workbench.fitWidth")}</button>
        <button onClick={props.onResetView} type="button">{t("workbench.resetView")}</button>
        <button onClick={props.onRerender} type="button">{t("workbench.rerender")}</button>
        <button onClick={props.onOpenMusicXmlTextPreview} type="button">{t("workbench.musicxmlText")}</button>
        <label>
          {t("workbench.layout")}
          <select value={props.layoutMode} onChange={(event) => props.onLayoutMode(event.target.value as ScoreLayoutMode)}>
            <option value="fit_width">{formatMusicTerm("fit_width", t)}</option>
            <option value="page">{formatMusicTerm("page", t)}</option>
            <option value="continuous">{formatMusicTerm("continuous", t)}</option>
            <option value="compact">{formatMusicTerm("compact", t)}</option>
            <option value="large_print">{formatMusicTerm("large_print", t)}</option>
          </select>
        </label>
        <label>
          {t("workbench.renderer")}
          <select value={props.rendererMode} onChange={(event) => props.onRendererMode(event.target.value)}>
            <option value="auto">{formatMusicTerm("auto", t)}</option>
            <option value="osmd">{formatMusicTerm("osmd", t)}</option>
            <option value="vexflow">{formatMusicTerm("vexflow", t)}</option>
            <option value="fallback">{formatMusicTerm("fallback", t)}</option>
          </select>
        </label>
      </div>
    </div>
  );
}
