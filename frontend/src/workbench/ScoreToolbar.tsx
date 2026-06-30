import type { NoteDuration } from "../score/noteInput";

type Props = {
  tool: string;
  zoom: number;
  rendererMode: string;
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
  onTie: () => void;
  onSlur: () => void;
};

const DURATIONS: NoteDuration[] = ["whole", "half", "quarter", "eighth", "sixteenth", "dotted_half", "dotted_quarter", "dotted_eighth", "triplet_eighth"];

export default function ScoreToolbar(props: Props) {
  return (
    <div className="workbench-toolbar notation-toolbar">
      <div className="toolbar-row">
        <strong>Sera Score Workbench</strong>
        <button className={props.editMode === "select" ? "active" : ""} onClick={() => props.onEditMode("select")} type="button">Select</button>
        <button className={props.editMode === "note_input" ? "active" : ""} onClick={() => props.onEditMode("note_input")} type="button">Note Input</button>
        {["note", "rest", "delete"].map((tool) => (
          <button className={props.tool === tool ? "active" : ""} key={tool} onClick={() => props.onTool(tool)} type="button">
            {tool}
          </button>
        ))}
      </div>
      <div className="toolbar-row">
        {DURATIONS.map((duration) => (
          <button className={props.duration === duration ? "active" : ""} key={duration} onClick={() => props.onDuration(duration)} type="button">
            {duration.replace("_", " ")}
          </button>
        ))}
        <button className={props.dotted ? "active" : ""} onClick={props.onDotted} type="button">Dot</button>
        {["", "sharp", "flat", "natural"].map((accidental) => (
          <button className={props.accidental === accidental ? "active" : ""} key={accidental || "none"} onClick={() => props.onAccidental(accidental)} type="button">
            {accidental || "natural off"}
          </button>
        ))}
        <button onClick={props.onTie} type="button">Tie</button>
        <button onClick={props.onSlur} type="button">Slur</button>
      </div>
      <div className="toolbar-row">
        <label>
          Staff
          <select value={props.staff} onChange={(event) => props.onStaff(event.target.value as "right_hand" | "left_hand")}>
            <option value="right_hand">right hand</option>
            <option value="left_hand">left hand</option>
          </select>
        </label>
        <label>
          Voice
          <select value={props.voice} onChange={(event) => props.onVoice(Number(event.target.value) as 1 | 2)}>
            <option value={1}>voice 1</option>
            <option value={2}>voice 2</option>
          </select>
        </label>
        <button disabled={!props.canUndo} onClick={props.onUndo} type="button">Undo</button>
        <button disabled={!props.canRedo} onClick={props.onRedo} type="button">Redo</button>
        <button onClick={props.onPlay} type="button">Play</button>
        <button onClick={props.onStop} type="button">Stop</button>
        <button className={props.loop ? "active" : ""} onClick={() => props.onLoop(!props.loop)} type="button">Loop</button>
      </div>
      <div className="toolbar-row">
        <button onClick={props.onNew} type="button">New</button>
        <label className="file-button">
          Import
          <input accept=".musicxml,.xml,.mxl" onChange={(event) => event.target.files?.[0] && props.onImport(event.target.files[0])} type="file" />
        </label>
        <label className="file-button">
          Open
          <input accept=".json,.sera.json" onChange={(event) => event.target.files?.[0] && props.onOpen(event.target.files[0])} type="file" />
        </label>
        <button onClick={props.onSave} type="button">Save</button>
        <button onClick={props.onExportMusicXml} type="button">MusicXML</button>
        <button onClick={props.onExportMidi} type="button">MIDI</button>
        <button onClick={props.onExportPdf} type="button">PDF</button>
        <label>
          Zoom
          <input max="1.8" min="0.7" onChange={(event) => props.onZoom(Number(event.target.value))} step="0.1" type="range" value={props.zoom} />
        </label>
        <button onClick={props.onFitWidth} type="button">Fit width</button>
        <label>
          Renderer
          <select value={props.rendererMode} onChange={(event) => props.onRendererMode(event.target.value)}>
            <option value="auto">auto</option>
            <option value="osmd">osmd</option>
            <option value="vexflow">vexflow</option>
            <option value="fallback">fallback</option>
          </select>
        </label>
      </div>
    </div>
  );
}
