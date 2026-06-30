import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyScorePatch,
  applyWorkbenchOperation,
  explainSelection,
  exportScoreMidi,
  exportScoreMusicXml,
  exportScorePdf,
  partialApplyScorePatch,
  importMusicXmlToScoreDocument,
  redoWorkbenchOperation,
  rejectScorePatch,
  requestAgentScoreEdit,
  saveScoreProject,
  undoWorkbenchOperation,
  validateScoreDocument
} from "../api.js";
import ArticulationPalette from "../components/ArticulationPalette";
import DurationPalette from "../components/DurationPalette";
import DynamicsPalette from "../components/DynamicsPalette";
import KeyboardShortcutsHelp from "../components/KeyboardShortcutsHelp";
import NotePalette from "../components/NotePalette";
import { generateLeftHandAccompanimentOperations } from "../score/accompanimentGeneration";
import { clearAutosave, loadAutosave, makeAutosavePayload, saveAutosave } from "../score/autosave";
import { buildDragOperations, transposePitch } from "../score/dragEditing";
import { mapWorkbenchShortcut } from "../score/keyboardShortcuts";
import { EMPTY_PLAYBACK_STATE, advanceFakePlayback, seekPlayback, type PlaybackState } from "../score/midiPlayback";
import { downloadTextFile } from "../score/musicxmlAdapter";
import {
  DEFAULT_NOTE_INPUT_CURSOR,
  advanceCursor,
  canInsertAtCursor,
  createInsertNoteOperation,
  createInsertRestOperation,
  fillMeasureWithRests,
  type NoteDuration,
  type NoteInputCursor
} from "../score/noteInput";
import { EMPTY_OPERATION_HISTORY } from "../score/operationHistory";
import { buildPlaybackMap, quarterFromMeasure } from "../score/playbackMap";
import { migrateWorkbenchProject } from "../score/projectMigration";
import type { HitTarget, RendererMode, RendererStatus } from "../score/renderers/renderTypes";
import { applyLocalOperation, recordLocalOperation, redoLocal, undoLocal } from "../score/scoreOperations";
import {
  clearSelection,
  EMPTY_SELECTION,
  selectAllMeasures,
  selectEvent,
  selectMeasure,
  selectMeasureRange,
  selectTargets,
  selectionSummary,
  selectionToRange
} from "../score/selection";
import { createEmptyScoreDocument, scoreDocumentFromResult } from "../score/scoreTypes";
import type { OperationHistory, ScoreDocument, ScoreOperation, ScorePatch } from "../score/scoreTypes";
import AgentEditPanel from "./AgentEditPanel";
import NoteInputMode from "./NoteInputMode";
import OperationHistoryPanel from "./OperationHistoryPanel";
import PatchPreviewPanel from "./PatchPreviewPanel";
import PlaybackScrubber from "./PlaybackScrubber";
import ScoreCanvas from "./ScoreCanvas";
import ScoreInspector from "./ScoreInspector";
import ScoreStatusBar from "./ScoreStatusBar";
import ScoreTimeline from "./ScoreTimeline";
import ScoreToolbar from "./ScoreToolbar";

export default function ScoreWorkbench({ result }: { result: any }) {
  const initialScore = useMemo(() => scoreDocumentFromResult(result), [result]);
  const [scoreDocument, setScoreDocument] = useState<ScoreDocument>(initialScore);
  const [history, setHistory] = useState<OperationHistory>(EMPTY_OPERATION_HISTORY);
  const [selection, setSelection] = useState({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
  const [hoverEventId, setHoverEventId] = useState("");
  const [tool, setTool] = useState("select");
  const [editMode, setEditMode] = useState<"select" | "note_input">("select");
  const [noteCursor, setNoteCursor] = useState<NoteInputCursor>(DEFAULT_NOTE_INPUT_CURSOR);
  const [noteWarning, setNoteWarning] = useState("");
  const [zoom, setZoom] = useState(1);
  const [rendererMode, setRendererMode] = useState<RendererMode>("auto");
  const [rendererStatus, setRendererStatus] = useState<RendererStatus>({ requestedMode: "auto", activeMode: "fallback", state: "idle", message: "renderer idle", renderMs: 0 });
  const [hitDebug, setHitDebug] = useState<Record<string, unknown>>({});
  const [showHitBoxes, setShowHitBoxes] = useState(false);
  const [instruction, setInstruction] = useState("Make selected measures more lyrical while preserving harmony.");
  const [agentConstraints, setAgentConstraints] = useState({ preserve_harmony: true, preserve_form: true, preserve_manual_edits: true, patch_size_limit: "small", target_staff: "both", target_voice: "all" });
  const [patchPreview, setPatchPreview] = useState<any>(null);
  const [agentPatchHistory, setAgentPatchHistory] = useState<ScorePatch[]>([]);
  const [explanation, setExplanation] = useState<any>(null);
  const [validation, setValidation] = useState<any>({});
  const [status, setStatus] = useState("workbench ready");
  const [dirtyMeasures, setDirtyMeasures] = useState<number[]>([]);
  const [recentOperations, setRecentOperations] = useState<ScoreOperation[]>([]);
  const [autosaveProject, setAutosaveProject] = useState<any>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState>(EMPTY_PLAYBACK_STATE);
  const playbackTickRef = useRef<number>(0);

  const selectedRange = useMemo(() => selectionToRange(scoreDocument, selection), [scoreDocument, selection]);
  const selectedSummary = useMemo(() => selectionSummary(scoreDocument, selection), [scoreDocument, selection]);
  const playbackMap = useMemo(() => buildPlaybackMap(scoreDocument), [scoreDocument]);
  const selectedMeasureId = selection.measureIds[selection.measureIds.length - 1] || "m1";
  const selectedEventId = selection.eventIds[selection.eventIds.length - 1] || "";
  const selectedMeasure = scoreDocument.measures.find((measure) => measure.measure_id === selectedMeasureId) || scoreDocument.measures[0];

  useEffect(() => {
    setScoreDocument(initialScore);
    setHistory(EMPTY_OPERATION_HISTORY);
    setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
    setPatchPreview(null);
    setAgentPatchHistory([]);
    setDirtyMeasures([]);
    setRecentOperations([]);
  }, [initialScore]);

  useEffect(() => {
    setNoteCursor((current) => ({ ...current, ...cursorMeasureFromSelection(scoreDocument, selection, current) }));
  }, [scoreDocument, selection]);

  useEffect(() => {
    const saved = loadAutosave();
    if (saved?.score_document?.score_id && saved.score_document.score_id !== initialScore.score_id) {
      setAutosaveProject(saved);
    }
  }, [initialScore.score_id]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      saveAutosave(
        makeAutosavePayload({
          scoreDocument,
          operationHistory: history,
          agentPatchHistory,
          originalPrompt: result?.prompt || "",
          compositionPlan: result?.plan || {},
          validationReports: validation ? [validation] : [],
          experimentMetadata: result?.metadata || {}
        })
      );
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [scoreDocument, history, agentPatchHistory, result, validation]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const action = mapWorkbenchShortcut(event, editMode);
      if (!action) return;
      event.preventDefault();
      if (action.type === "set_duration") setNoteCursor((current) => ({ ...current, duration: action.duration, dotted: action.duration.startsWith("dotted_") }));
      if (action.type === "toggle_dotted") setNoteCursor((current) => ({ ...current, dotted: !current.dotted }));
      if (action.type === "input_pitch") handleInputPitch(action.step, action.chordTone);
      if (action.type === "input_rest") handleInputRest();
      if (action.type === "transpose") transposeSelected(action.semitones);
      if (action.type === "delete_selection") deleteSelected();
      if (action.type === "undo") handleUndo();
      if (action.type === "redo") handleRedo();
      if (action.type === "toggle_playback") playbackState.playing ? handleStop() : handlePlay();
      if (action.type === "clear_or_select_mode") {
        if (editMode === "note_input") setEditMode("select");
        else setSelection(clearSelection());
      }
      if (action.type === "select_all") setSelection(selectAllMeasures(scoreDocument));
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editMode, noteCursor, selection, scoreDocument, history, playbackState]);

  useEffect(() => {
    if (!playbackState.playing) return;
    playbackTickRef.current = performance.now();
    const timer = window.setInterval(() => {
      const now = performance.now();
      const elapsed = now - playbackTickRef.current;
      playbackTickRef.current = now;
      const loopStart = quarterFromMeasure(playbackMap, selectedRange.start_measure);
      const loopEnd = quarterFromMeasure(playbackMap, selectedRange.end_measure + 1) || playbackMap.totalQuarters;
      setPlaybackState((current) => advanceFakePlayback(playbackMap, current, elapsed, loopStart, loopEnd));
    }, 180);
    return () => window.clearInterval(timer);
  }, [playbackState.playing, playbackState.loop, playbackMap, selectedRange]);

  async function runOperation(operation: ScoreOperation) {
    if (playbackState.playing) handleStop();
    setStatus("applying operation");
    try {
      const payload = await applyWorkbenchOperation(scoreDocument, operation, history);
      setScoreDocument(payload.score_document);
      setHistory(payload.operation_history);
      setValidation(payload.validation_report || {});
      rememberOperations([payload.operation]);
      setDirtyMeasures(markDirtyFromOperation(payload.operation));
      setStatus("operation applied");
    } catch {
      const payload = applyLocalOperation(scoreDocument, operation);
      setScoreDocument(payload.scoreDocument);
      setHistory(recordLocalOperation(history, payload.operation));
      rememberOperations([payload.operation]);
      setDirtyMeasures(markDirtyFromOperation(payload.operation));
      setStatus("operation applied locally");
    }
  }

  function runOperations(operations: ScoreOperation[], label = "operations applied locally") {
    if (!operations.length) return;
    if (playbackState.playing) handleStop();
    let current = scoreDocument;
    let currentHistory = history;
    const applied: ScoreOperation[] = [];
    for (const operation of operations) {
      const payload = applyLocalOperation(current, operation);
      current = payload.scoreDocument;
      currentHistory = recordLocalOperation(currentHistory, payload.operation);
      applied.push(payload.operation);
    }
    setScoreDocument(current);
    setHistory(currentHistory);
    rememberOperations(applied);
    setDirtyMeasures(uniqueNumbers(applied.flatMap((operation) => markDirtyFromOperation(operation))));
    setStatus(label);
  }

  async function handleUndo() {
    try {
      const payload = await undoWorkbenchOperation(scoreDocument, history);
      setScoreDocument(payload.score_document);
      setHistory(payload.operation_history);
      setValidation(payload.validation_report || {});
    } catch {
      const payload = undoLocal(scoreDocument, history);
      setScoreDocument(payload.scoreDocument);
      setHistory(payload.operationHistory);
    }
  }

  async function handleRedo() {
    try {
      const payload = await redoWorkbenchOperation(scoreDocument, history);
      setScoreDocument(payload.score_document);
      setHistory(payload.operation_history);
      setValidation(payload.validation_report || {});
    } catch {
      const payload = redoLocal(scoreDocument, history);
      setScoreDocument(payload.scoreDocument);
      setHistory(payload.operationHistory);
    }
  }

  async function handleAgentEdit(value = instruction, constraintsOverride = agentConstraints) {
    setStatus("previewing agent patch");
    try {
      const preview = await requestAgentScoreEdit(scoreDocument, value, selectedRange, constraintsOverride, {
        current_selection: selectedSummary,
        recent_operations: recentOperations,
        dirty_measures: dirtyMeasures,
        validation_warnings: validation?.warnings || [],
        playback_position: playbackState,
        selected_notes_summary: selectedSummary,
        user_edit_intent_inferred: inferUserEditIntent(recentOperations),
        preserve_user_edits_since_timestamp: [...recentOperations].reverse().find((operation) => operation.source === "user")?.timestamp || ""
      });
      setPatchPreview(preview);
      setValidation(preview.validation_report || {});
      setStatus("patch preview ready");
    } catch (error: any) {
      setStatus(`agent edit failed: ${error.message}`);
    }
  }

  async function handleAcceptPatch() {
    if (!patchPreview?.patch) return;
    try {
      const payload = await applyScorePatch(scoreDocument, patchPreview.patch, instruction, selectedRange, agentConstraints);
      if (payload.accepted) {
        setScoreDocument(payload.score_document);
        setPatchPreview(null);
        setValidation(payload.validation_report || {});
        const operations = payload.patch?.operations || [];
        setHistory((current) => ({ done: [...current.done, ...operations], undone: [] }));
        rememberOperations(operations);
        setAgentPatchHistory((current) => [...current, payload.patch]);
        setStatus("patch accepted");
      } else {
        setStatus(payload.rejection_reason || "patch rejected by validator");
      }
    } catch (error: any) {
      setStatus(`patch apply failed: ${error.message}`);
    }
  }

  async function handlePartialPatch(options: { operation_indexes?: number[]; apply_filter?: string }) {
    if (!patchPreview?.patch) return;
    try {
      const payload = await partialApplyScorePatch(scoreDocument, patchPreview.patch, instruction, selectedRange, agentConstraints, options);
      if (payload.accepted) {
        setScoreDocument(payload.score_document);
        setPatchPreview(null);
        setValidation(payload.validation_report || {});
        const operations = payload.patch?.operations || [];
        setHistory((current) => ({ done: [...current.done, ...operations], undone: [] }));
        rememberOperations(operations);
        setAgentPatchHistory((current) => [...current, payload.patch]);
        setStatus("partial patch applied");
      } else {
        setStatus(payload.rejection_reason || "partial patch rejected by validator");
      }
    } catch (error: any) {
      setStatus(`partial apply failed: ${error.message}`);
    }
  }

  async function handleExplainSelection(question = instruction) {
    setStatus("explaining selection");
    try {
      const payload = await explainSelection(scoreDocument, selectedRange, question);
      setExplanation(payload.explanation);
      setStatus("selection explanation ready");
    } catch (error: any) {
      setStatus(`explain failed: ${error.message}`);
    }
  }

  async function handleRejectPatch() {
    if (!patchPreview?.patch) return;
    try {
      await rejectScorePatch(scoreDocument, patchPreview.patch);
      setAgentPatchHistory((current) => [...current, patchPreview.patch]);
    } catch {
      // Local rejection is still valid because the score has not changed.
    }
    setPatchPreview(null);
    setStatus("patch rejected");
  }

  async function handleImport(file: File) {
    const musicxml = await file.text();
    try {
      const payload = await importMusicXmlToScoreDocument(musicxml, "Imported through Score Workbench");
      setScoreDocument(payload.score_document);
      setHistory(payload.operation_history || EMPTY_OPERATION_HISTORY);
      setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
      setStatus("MusicXML imported");
    } catch (error: any) {
      setStatus(`import failed: ${error.message}`);
    }
  }

  async function handleOpenProject(file: File) {
    const project = migrateWorkbenchProject(JSON.parse(await file.text()));
    setScoreDocument(project.score_document);
    setHistory(project.operation_history);
    setAgentPatchHistory(project.agent_patch_history);
    setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
    setStatus("project opened and migrated to V0.8");
  }

  async function handleExportMusicXml() {
    try {
      const payload = await exportScoreMusicXml(scoreDocument);
      downloadTextFile(`${scoreDocument.score_id}.musicxml`, payload.musicxml);
      setValidation(payload.validation_report || {});
      setStatus("MusicXML exported");
    } catch (error: any) {
      setStatus(`MusicXML export failed: ${error.message}`);
    }
  }

  async function handleExportMidi() {
    try {
      const payload = await exportScoreMidi(scoreDocument);
      setStatus(`MIDI exported: ${payload.midi_path}`);
    } catch (error: any) {
      setStatus(`MIDI export failed: ${error.message}`);
    }
  }

  async function handleExportPdf() {
    try {
      const payload = await exportScorePdf(scoreDocument);
      setStatus(`PDF exported: ${payload.pdf_path}`);
    } catch (error: any) {
      setStatus(`PDF export failed: ${error.message}`);
    }
  }

  async function handleSaveProject() {
    const project = makeAutosavePayload({
      scoreDocument,
      operationHistory: history,
      agentPatchHistory,
      originalPrompt: result?.prompt || "",
      compositionPlan: result?.plan || {},
      validationReports: validation ? [validation] : [],
      experimentMetadata: result?.metadata || {}
    });
    downloadTextFile(`${scoreDocument.score_id}.sera.json`, JSON.stringify(project, null, 2));
    clearAutosave();
    try {
      await saveScoreProject(scoreDocument.score_id, project);
    } catch {
      // Browser download remains the fallback project save.
    }
    setStatus("project saved");
  }

  async function refreshValidation() {
    try {
      const payload = await validateScoreDocument(scoreDocument);
      setValidation(payload.validation_report || {});
    } catch {
      setValidation({ warnings: ["local validation fallback"] });
    }
  }

  function handleInputPitch(step: string, chordTone = false) {
    const check = canInsertAtCursor(scoreDocument, noteCursor);
    if (!check.ok) {
      setNoteWarning(check.warning);
      return;
    }
    runOperation(createInsertNoteOperation(scoreDocument, noteCursor, step, chordTone));
    setNoteCursor((current) => advanceCursor(scoreDocument, current));
    setNoteWarning("");
  }

  function handleInputRest() {
    const check = canInsertAtCursor(scoreDocument, noteCursor);
    if (!check.ok) {
      setNoteWarning(check.warning);
      return;
    }
    runOperation(createInsertRestOperation(scoreDocument, noteCursor));
    setNoteCursor((current) => advanceCursor(scoreDocument, current));
    setNoteWarning("");
  }

  function handleCanvasNoteInput(target: HitTarget | null, point: { x: number; y: number }, chordTone: boolean) {
    const measure = scoreDocument.measures.find((item) => item.measure_id === target?.measureId) || selectedMeasure;
    if (!measure) return;
    const staff = point.y > 126 ? "left_hand" : "right_hand";
    const offset = Math.max(0, Math.round(((point.x - 58) % 128) / 22) * 0.5);
    const cursor = { ...noteCursor, measureId: measure.measure_id, measureNumber: measure.number, staff: staff as "right_hand" | "left_hand", offset };
    setNoteCursor(cursor);
    const pitch = pitchFromCanvasPoint(point.y, staff);
    const check = canInsertAtCursor(scoreDocument, cursor);
    if (!check.ok) {
      setNoteWarning(check.warning);
      return;
    }
    const operation = createInsertNoteOperation(scoreDocument, cursor, pitch[0], chordTone);
    runOperation({ ...operation, after: { ...operation.after, pitch } });
  }

  function insertPitch(pitch: string) {
    if (tool === "rest") {
      handleInputRest();
      return;
    }
    const octave = Number(pitch.match(/\d/)?.[0] || noteCursor.octave);
    const cursor = { ...noteCursor, octave };
    const operation = createInsertNoteOperation(scoreDocument, cursor, pitch[0]);
    runOperation({ ...operation, after: { ...operation.after, pitch } });
    setNoteCursor((current) => advanceCursor(scoreDocument, current));
  }

  function updateSelectedDuration(duration: string) {
    if (duration === "rest") {
      runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "convert_note_to_rest", { duration: "quarter" })), "converted notes to rests");
      return;
    }
    if (!selectedEventId) return;
    runOperation(operationForSelectedEvent(selectedEventId, "update_duration", { duration }));
  }

  function updateSelectedDynamic(dynamic: string) {
    if (!selectedEventId) return;
    runOperation(operationForSelectedEvent(selectedEventId, "change_dynamic", { dynamic }));
  }

  function transposeSelected(semitones: number) {
    if (selection.eventIds.length) {
      const operations = selection.eventIds.map((eventId) => {
        const found = findEvent(scoreDocument, eventId);
        return operationForSelectedEvent(eventId, "update_pitch", { pitch: found?.event?.pitch ? transposePitch(found.event.pitch, semitones) : "C4" });
      });
      runOperations(operations, "selection transposed");
      return;
    }
    runOperation({ source: "user", type: "transpose_selection", target: selectedRange, after: { semitones }, description: `Transpose selected range ${semitones}` });
  }

  function deleteSelected() {
    runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "delete_note", {})), "selection deleted");
  }

  function tieSelected() {
    runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "update_tie", { tie: "continue" })), "tie applied");
  }

  function slurSelected() {
    runOperations(selection.eventIds.map((eventId, index) => operationForSelectedEvent(eventId, "add_slur", { slur: index === 0 ? "start" : index === selection.eventIds.length - 1 ? "stop" : "continue" })), "slur applied");
  }

  function fillCurrentMeasureWithRests() {
    runOperations(fillMeasureWithRests(scoreDocument, noteCursor), "measure filled with rests");
  }

  function generateAccompaniment() {
    runOperations(generateLeftHandAccompanimentOperations(scoreDocument, selectedRange.start_measure, selectedRange.end_measure, "arpeggiated"), "left-hand accompaniment generated");
  }

  function handlePlay() {
    const start = selectedRange.start_measure ? quarterFromMeasure(playbackMap, selectedRange.start_measure) : playbackState.currentQuarter;
    setPlaybackState((current) => ({ ...seekPlayback(playbackMap, start, current), playing: true }));
    setStatus("fake playback active");
  }

  function handleStop() {
    setPlaybackState((current) => ({ ...current, playing: false }));
  }

  function seekPlaybackQuarter(quarter: number) {
    setPlaybackState((current) => seekPlayback(playbackMap, quarter, current));
  }

  function rememberOperations(operations: ScoreOperation[]) {
    setRecentOperations((current) => [...current, ...operations].slice(-24));
  }

  function operationForSelectedEvent(eventId: string, type: string, after: Record<string, unknown>): ScoreOperation {
    const found = findEvent(scoreDocument, eventId);
    return {
      source: "user",
      type,
      target: { measure_id: found?.measure.measure_id || selectedMeasureId, measure: found?.measure.number || selectedMeasure?.number || 1, event_id: eventId },
      after,
      description: `${type.replaceAll("_", " ")} ${eventId}`
    };
  }

  return (
    <section className="workbench-shell">
      <ScoreToolbar
        accidental={noteCursor.accidental}
        canRedo={history.undone.length > 0}
        canUndo={history.done.length > 0}
        dotted={noteCursor.dotted}
        duration={noteCursor.duration}
        editMode={editMode}
        loop={playbackState.loop}
        onAccidental={(accidental) => setNoteCursor((current) => ({ ...current, accidental: accidental as NoteInputCursor["accidental"] }))}
        onDotted={() => setNoteCursor((current) => ({ ...current, dotted: !current.dotted }))}
        onDuration={(duration: NoteDuration) => setNoteCursor((current) => ({ ...current, duration, dotted: duration.startsWith("dotted_") }))}
        onEditMode={setEditMode}
        onExportMidi={handleExportMidi}
        onExportMusicXml={handleExportMusicXml}
        onExportPdf={handleExportPdf}
        onFitWidth={() => setZoom(1)}
        onImport={handleImport}
        onLoop={(loop) => setPlaybackState((current) => ({ ...current, loop }))}
        onNew={() => { setScoreDocument(createEmptyScoreDocument(8)); setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" }); }}
        onOpen={handleOpenProject}
        onPlay={handlePlay}
        onRedo={handleRedo}
        onRendererMode={(mode) => setRendererMode(mode as RendererMode)}
        onSave={handleSaveProject}
        onSlur={slurSelected}
        onStaff={(staff) => setNoteCursor((current) => ({ ...current, staff }))}
        onStop={handleStop}
        onTie={tieSelected}
        onTool={setTool}
        onUndo={handleUndo}
        onVoice={(voice) => setNoteCursor((current) => ({ ...current, voice }))}
        onZoom={setZoom}
        rendererMode={rendererMode}
        staff={noteCursor.staff}
        tool={tool}
        voice={noteCursor.voice}
        zoom={zoom}
      />
      {autosaveProject && (
        <section className="autosave-banner">
          <strong>Unsaved V0.8 project found</strong>
          <button onClick={() => { const project = migrateWorkbenchProject(autosaveProject); setScoreDocument(project.score_document); setHistory(project.operation_history); setAgentPatchHistory(project.agent_patch_history); setAutosaveProject(null); }} type="button">Recover</button>
          <button onClick={() => { clearAutosave(); setAutosaveProject(null); }} type="button">Discard</button>
        </section>
      )}
      <div className="workbench-grid">
        <aside className="workbench-left">
          <NoteInputMode
            cursor={noteCursor}
            editMode={editMode}
            onCursor={setNoteCursor}
            onDuration={(duration) => setNoteCursor((current) => ({ ...current, duration, dotted: duration.startsWith("dotted_") }))}
            onEditMode={setEditMode}
            onFillRests={fillCurrentMeasureWithRests}
            warning={noteWarning}
          />
          <NotePalette onInsert={insertPitch} onTranspose={transposeSelected} />
          <DurationPalette onSelect={updateSelectedDuration} />
          <DynamicsPalette onSelect={updateSelectedDynamic} />
          <ArticulationPalette onSelect={(item) => selectedEventId && runOperation(operationForSelectedEvent(selectedEventId, "update_articulation", { articulations: [item] }))} />
          <section className="workbench-tool-group">
            <h3>Lines and Staff</h3>
            <div className="palette-grid">
              <button onClick={tieSelected} type="button">Tie</button>
              <button onClick={slurSelected} type="button">Slur</button>
              <button onClick={() => runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "update_staff", { staff: "left_hand" })), "moved to left hand")} type="button">To LH</button>
              <button onClick={() => runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "update_staff", { staff: "right_hand" })), "moved to right hand")} type="button">To RH</button>
              <button onClick={generateAccompaniment} type="button">Generate LH</button>
            </div>
          </section>
          <KeyboardShortcutsHelp />
        </aside>
        <main className="workbench-center">
          <ScoreCanvas
            editMode={editMode}
            hoverEventId={hoverEventId}
            onClearSelection={() => setSelection(clearSelection())}
            onDragEdit={(eventIds, deltaY, deltaX, duplicate) => runOperations(buildDragOperations(scoreDocument, eventIds, deltaY, deltaX, duplicate), "drag edit applied")}
            onHitDebug={setHitDebug}
            onHoverEvent={setHoverEventId}
            onNoteInput={handleCanvasNoteInput}
            onRenderStatus={setRendererStatus}
            onSelectAll={() => setSelection(selectAllMeasures(scoreDocument))}
            onSelectEvent={(eventId, measureId, additive) => setSelection((current) => selectEvent(current, eventId, measureId, additive))}
            onSelectMeasure={(measureId, additive, rangeSelect) => setSelection((current) => rangeSelect ? selectMeasureRange(scoreDocument, current.anchorMeasureId || current.measureIds[0] || measureId, measureId) : selectMeasure(current, measureId, additive))}
            onSelectTargets={(targets) => setSelection(selectTargets(targets))}
            patchRange={patchPreview?.patch?.target_range}
            playbackMeasure={playbackState.currentMeasure}
            rendererMode={rendererMode}
            scoreDocument={scoreDocument}
            selectedEventIds={selection.eventIds}
            selectedMeasureIds={selection.measureIds}
            showHitBoxes={showHitBoxes}
            validationWarnings={validation?.warnings || []}
            zoom={zoom}
          />
          <PlaybackScrubber
            onLoop={(loop) => setPlaybackState((current) => ({ ...current, loop }))}
            onPlay={handlePlay}
            onSeek={seekPlaybackQuarter}
            onStop={handleStop}
            playbackMap={playbackMap}
            playbackState={playbackState}
            selectedEndMeasure={selectedRange.end_measure}
            selectedStartMeasure={selectedRange.start_measure}
          />
          <ScoreTimeline
            onSelectMeasure={(measureId) => { setSelection((current) => selectMeasure(current, measureId)); setPlaybackState((current) => seekPlayback(playbackMap, quarterFromMeasure(playbackMap, Number(measureId.replace(/\D/g, "")) || 1), current)); }}
            playbackMeasure={playbackState.currentMeasure}
            scoreDocument={scoreDocument}
            selectedMeasureId={selectedMeasureId}
          />
          <OperationHistoryPanel history={history} />
        </main>
        <aside className="workbench-right">
          <ScoreInspector onOperation={runOperation} scoreDocument={scoreDocument} selectedEventId={selectedEventId} selectedMeasureId={selectedMeasureId} />
          <section className="workbench-panel hit-debug-panel">
            <h2>Hit Mapping</h2>
            <label className="inline-check">
              <input checked={showHitBoxes} onChange={(event) => setShowHitBoxes(event.target.checked)} type="checkbox" />
              show hit boxes
            </label>
            <pre>{JSON.stringify({ selected: selectedSummary, hitDebug, dirtyMeasures }, null, 2)}</pre>
          </section>
          <AgentEditPanel
            constraints={agentConstraints}
            disabled={status.includes("previewing")}
            instruction={instruction}
            onAgentEdit={handleAgentEdit}
            onConstraintsChange={setAgentConstraints}
            onExplain={handleExplainSelection}
            selectedRange={selectedRange}
            setInstruction={setInstruction}
          />
          <PatchPreviewPanel onAccept={handleAcceptPatch} onPartialApply={handlePartialPatch} onRegenerate={() => handleAgentEdit()} onReject={handleRejectPatch} preview={patchPreview} />
          {explanation && (
            <section className="workbench-panel">
              <h2>Selection Explanation</h2>
              <p>{explanation.summary}</p>
              <p>{explanation.harmony_analysis}</p>
              <p>{explanation.melodic_analysis}</p>
              <p>{explanation.rhythmic_analysis}</p>
            </section>
          )}
          <section className="workbench-panel">
            <h2>Validation</h2>
            <button onClick={refreshValidation} type="button">Run validator</button>
            <pre>{JSON.stringify(validation || {}, null, 2)}</pre>
          </section>
        </aside>
      </div>
      <ScoreStatusBar history={history} rendererStatus={`${rendererStatus.activeMode} ${rendererStatus.state} ${rendererStatus.renderMs}ms`} scoreDocument={scoreDocument} status={`${status}; playback M${playbackState.currentMeasure || "-"}; recent ops ${recentOperations.length}`} />
    </section>
  );
}

function cursorMeasureFromSelection(score: ScoreDocument, selection: { measureIds: string[]; eventIds: string[] }, current: NoteInputCursor) {
  const measure = score.measures.find((item) => selection.measureIds.includes(item.measure_id)) || score.measures[0];
  if (!measure) return current;
  const event = measure.events.find((item) => selection.eventIds.includes(item.event_id));
  return {
    measureId: measure.measure_id,
    measureNumber: measure.number,
    offset: event?.offset ?? current.offset,
    staff: (event?.staff as NoteInputCursor["staff"]) || current.staff,
    voice: (event?.voice === 2 ? 2 : 1) as 1 | 2
  };
}

function findEvent(score: ScoreDocument, eventId: string) {
  for (const measure of score.measures) {
    const event = measure.events.find((item) => item.event_id === eventId);
    if (event) return { measure, event };
  }
  return null;
}

function markDirtyFromOperation(operation: ScoreOperation) {
  const target = operation.target || {};
  const values = [target.measure, target.measure_number, target.start_measure, target.end_measure]
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value > 0);
  if (values.length) {
    const start = Math.min(...values);
    const end = Math.max(...values);
    return Array.from({ length: end - start + 1 }, (_, index) => start + index);
  }
  const measureId = String(target.measure_id || "");
  const parsed = Number(measureId.replace(/\D/g, ""));
  return parsed ? [parsed] : [];
}

function uniqueNumbers(values: number[]) {
  return Array.from(new Set(values)).sort((a, b) => a - b);
}

function pitchFromCanvasPoint(y: number, staff: string) {
  if (staff === "left_hand") {
    const pitches = ["C3", "D3", "E3", "F3", "G3", "A3", "B3"];
    return pitches[Math.max(0, Math.min(pitches.length - 1, Math.round((174 - y) / 8) + 2))];
  }
  const pitches = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"];
  return pitches[Math.max(0, Math.min(pitches.length - 1, Math.round((112 - y) / 7) + 2))];
}

function inferUserEditIntent(operations: ScoreOperation[]) {
  const recent = operations.slice(-6).map((operation) => operation.type);
  if (recent.some((type) => type.includes("pitch") || type.includes("transpose"))) return "melody shaping";
  if (recent.some((type) => type.includes("duration") || type.includes("rhythm"))) return "rhythm editing";
  if (recent.some((type) => type.includes("dynamic") || type.includes("articulation"))) return "expression editing";
  return "local score editing";
}
