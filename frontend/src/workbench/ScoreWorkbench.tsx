import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyStrictScorePatch,
  applyScorePatch,
  applyWorkbenchOperation,
  createNotationBridgeSession,
  explainSelection,
  exportNotationBridgeRevision,
  exportScoreMidi,
  exportScoreMusicXml,
  exportScorePdf,
  generateStrictScorePatchPreview,
  getNotationHosts,
  getNotationBridgeWorkspace,
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
import { createClickToNotateOperation, type ClickToNotatePreview } from "../score/clickToNotate";
import { readPendingDesktopSession, subscribeDesktopOpenSession } from "../desktop/desktopRuntime";
import { buildDragOperations, transposePitch } from "../score/dragEditing";
import { layoutConfigForMode, type ScoreLayoutMode } from "../score/layoutConfig";
import { formatDuration, formatMusicTerm, type Translate } from "../i18n/musicTerms";
import { mapWorkbenchShortcut } from "../score/keyboardShortcuts";
import { EMPTY_PLAYBACK_STATE, advanceFakePlayback, seekPlayback, type PlaybackState } from "../score/midiPlayback";
import { downloadTextFile, scoreDocumentToSimpleMusicXml } from "../score/musicxmlAdapter";
import {
  DEFAULT_NOTE_INPUT_CURSOR,
  advanceCursor,
  canInsertAtCursor,
  createInsertNoteOperation,
  createInsertRestOperation,
  fillMeasureWithRests,
  pitchFromStep,
  type NoteDuration,
  type NoteInputCursor
} from "../score/noteInput";
import { EMPTY_OPERATION_HISTORY } from "../score/operationHistory";
import { bridgeSessionIdFromSearch, safeBridgeSessionId, selectionFromNotationHostContext } from "../score/notationBridge";
import { buildPlaybackMap, quarterFromMeasure } from "../score/playbackMap";
import { migrateWorkbenchProject } from "../score/projectMigration";
import {
  buildStrictScoreScopes,
  EMPTY_STRICT_PATCH_HISTORY,
  measureRangeForScope,
  recordStrictPatch,
  redoStrictPatch,
  undoStrictPatch,
  type StrictPatchHistory
} from "../score/seraEditResearch";
import type { HitTarget, RendererMode, RendererStatus } from "../score/renderers/renderTypes";
import {
  jumpScoreCursorBoundary,
  jumpScoreCursorMeasure,
  moveScoreCursor,
  noteInputFromScoreCursor,
  scoreCursorFromNoteInput,
  switchCursorStaff,
  switchCursorVoice,
  transposeCursorPitch,
  validateScoreCursor,
  type ScoreCursor,
  type ScoreCursorSnap
} from "../score/scoreCursor";
import { applyLocalOperation, recordLocalOperation, redoLocal, undoLocal } from "../score/scoreOperations";
import { useI18n } from "../i18n/useI18n";
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
import type {
  OperationHistory,
  ScoreDocument,
  ScoreOperation,
  ScorePatch,
  StrictGenerationPreview
} from "../score/scoreTypes";
import AgentEditPanel from "./AgentEditPanel";
import LocationBar from "./LocationBar";
import MusicalityControlPanel, { DEFAULT_MUSICALITY_CONTROLS, type MusicalityControls } from "./MusicalityControlPanel";
import NoteInputMode from "./NoteInputMode";
import OperationHistoryPanel from "./OperationHistoryPanel";
import PatchPreviewPanel from "./PatchPreviewPanel";
import PlaybackScrubber from "./PlaybackScrubber";
import ScoreCanvas from "./ScoreCanvas";
import ScoreInspector from "./ScoreInspector";
import SeraEditResearchPanel from "./SeraEditResearchPanel";
import StrictScoreComparison from "./StrictScoreComparison";
import ScoreStatusBar from "./ScoreStatusBar";
import ScoreTimeline from "./ScoreTimeline";
import ScoreToolbar from "./ScoreToolbar";

export default function ScoreWorkbench({ result }: { result: any }) {
  const { t } = useI18n();
  const initialScore = useMemo(() => scoreDocumentFromResult(result), [result]);
  const [scoreDocument, setScoreDocument] = useState<ScoreDocument>(initialScore);
  const [history, setHistory] = useState<OperationHistory>(EMPTY_OPERATION_HISTORY);
  const [selection, setSelection] = useState({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
  const [hoverEventId, setHoverEventId] = useState("");
  const [tool, setTool] = useState("select");
  const [editMode, setEditMode] = useState<"select" | "note_input">("select");
  const [noteCursor, setNoteCursor] = useState<NoteInputCursor>(DEFAULT_NOTE_INPUT_CURSOR);
  const [cursorSnap, setCursorSnap] = useState<ScoreCursorSnap>("beat");
  const [cursorPitch, setCursorPitch] = useState("C4");
  const [noteWarning, setNoteWarning] = useState("");
  const [zoom, setZoom] = useState(1);
  const [layoutMode, setLayoutMode] = useState<ScoreLayoutMode>("fit_width");
  const [renderNonce, setRenderNonce] = useState(0);
  const [musicXmlPreviewOpen, setMusicXmlPreviewOpen] = useState(false);
  const [rendererMode, setRendererMode] = useState<RendererMode>(result ? "auto" : "fallback");
  const [rendererStatus, setRendererStatus] = useState<RendererStatus>({ requestedMode: result ? "auto" : "fallback", activeMode: "fallback", state: "idle", message: "renderer idle", renderMs: 0 });
  const [hitDebug, setHitDebug] = useState<Record<string, unknown>>({});
  const [showHitBoxes, setShowHitBoxes] = useState(false);
  const [showBeatGrid, setShowBeatGrid] = useState(true);
  const [hoverTarget, setHoverTarget] = useState<HitTarget | null>(null);
  const [clickPreview, setClickPreview] = useState<ClickToNotatePreview | null>(null);
  const [instruction, setInstruction] = useState("Transpose the selected notes up a major second while preserving rhythm.");
  const [agentConstraints, setAgentConstraints] = useState({ preserve_harmony: true, preserve_form: true, preserve_manual_edits: true, patch_size_limit: "small", target_staff: "both", target_voice: "all" });
  const [musicalityControls, setMusicalityControls] = useState<MusicalityControls>(DEFAULT_MUSICALITY_CONTROLS);
  const [patchPreview, setPatchPreview] = useState<any>(null);
  const [agentWorkflow, setAgentWorkflow] = useState<"strict" | "legacy">("strict");
  const [strictGeneration, setStrictGeneration] = useState<StrictGenerationPreview | null>(null);
  const [strictBusy, setStrictBusy] = useState(false);
  const [strictHistory, setStrictHistory] = useState<StrictPatchHistory>(EMPTY_STRICT_PATCH_HISTORY);
  const [agentPatchHistory, setAgentPatchHistory] = useState<ScorePatch[]>([]);
  const [explanation, setExplanation] = useState<any>(null);
  const [validation, setValidation] = useState<any>({});
  const [status, setStatus] = useState("workbench ready");
  const [dirtyMeasures, setDirtyMeasures] = useState<number[]>([]);
  const [recentOperations, setRecentOperations] = useState<ScoreOperation[]>([]);
  const [autosaveProject, setAutosaveProject] = useState<any>(null);
  const [playbackState, setPlaybackState] = useState<PlaybackState>(EMPTY_PLAYBACK_STATE);
  const [notationHosts, setNotationHosts] = useState<any[]>([]);
  const [bridgeHost, setBridgeHost] = useState("musescore");
  const [bridgeSession, setBridgeSession] = useState<any>(null);
  const [bridgeDeepLinkSessionId, setBridgeDeepLinkSessionId] = useState(() => {
    if (typeof window === "undefined") return "";
    const querySession = bridgeSessionIdFromSearch(window.location.search);
    if (querySession) return querySession;
    return safeBridgeSessionId(readPendingDesktopSession().session_id);
  });
  const playbackTickRef = useRef<number>(0);

  const selectedRange = useMemo(() => selectionToRange(scoreDocument, selection), [scoreDocument, selection]);
  const selectedSummary = useMemo(() => selectionSummary(scoreDocument, selection), [scoreDocument, selection]);
  const strictScopes = useMemo(
    () => buildStrictScoreScopes(selectedRange, selection.eventIds, agentConstraints),
    [agentConstraints, selectedRange, selection.eventIds]
  );
  const strictPatchRange = useMemo(
    () => strictGeneration?.patch
      ? measureRangeForScope(scoreDocument, strictGeneration.patch.target_scope, selectedRange)
      : selectedRange,
    [scoreDocument, selectedRange, strictGeneration]
  );
  const playbackMap = useMemo(() => buildPlaybackMap(scoreDocument), [scoreDocument]);
  const selectedMeasureId = selection.measureIds[selection.measureIds.length - 1] || "m1";
  const selectedEventId = selection.eventIds[selection.eventIds.length - 1] || "";
  const selectedMeasure = scoreDocument.measures.find((measure) => measure.measure_id === selectedMeasureId) || scoreDocument.measures[0];
  const scoreCursor = useMemo(
    () => validateScoreCursor(scoreDocument, { ...scoreCursorFromNoteInput(noteCursor, editMode, scoreDocument, cursorSnap), pitch: cursorPitch }),
    [cursorPitch, cursorSnap, editMode, noteCursor, scoreDocument]
  );

  useEffect(() => {
    getNotationHosts()
      .then((payload) => setNotationHosts(payload.hosts || []))
      .catch(() => setNotationHosts([]));
  }, []);

  useEffect(() => {
    setScoreDocument(initialScore);
    setHistory(EMPTY_OPERATION_HISTORY);
    setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
    setPatchPreview(null);
    setStrictGeneration(null);
    setStrictHistory(EMPTY_STRICT_PATCH_HISTORY);
    setAgentPatchHistory([]);
    setDirtyMeasures([]);
    setRecentOperations([]);
  }, [initialScore]);

  useEffect(() => {
    if (!bridgeDeepLinkSessionId) return;
    let cancelled = false;
    setStatus("loading MuseScore bridge session");
    getNotationBridgeWorkspace(bridgeDeepLinkSessionId)
      .then((payload) => {
        if (cancelled) return;
        const restoredScore = payload.score_document as ScoreDocument;
        setScoreDocument(restoredScore);
        setHistory(payload.operation_history || EMPTY_OPERATION_HISTORY);
        setBridgeSession(payload.session);
        setBridgeHost(payload.session?.host_id || "musescore");
        setSelection(selectionFromNotationHostContext(restoredScore, payload.session?.host_context));
        setPatchPreview(null);
        setStrictGeneration(null);
        setStrictHistory(EMPTY_STRICT_PATCH_HISTORY);
        setAgentPatchHistory([]);
        setDirtyMeasures([]);
        setRecentOperations([]);
        setStatus(`${payload.session?.host_id || "notation"} bridge session restored`);
      })
      .catch((error: any) => {
        if (!cancelled) setStatus(`bridge session load failed: ${error.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [bridgeDeepLinkSessionId]);

  useEffect(() => {
    return subscribeDesktopOpenSession((payload) => {
      const sessionId = safeBridgeSessionId(payload.session_id);
      if (!sessionId) return;
      const url = new URL(window.location.href);
      url.searchParams.set("bridge_session", sessionId);
      url.searchParams.set("desktop", "1");
      window.history.replaceState({}, "", url);
      setBridgeDeepLinkSessionId(sessionId);
    });
  }, []);

  useEffect(() => {
    setNoteCursor((current) => ({ ...current, ...cursorMeasureFromSelection(scoreDocument, selection, current) }));
    const selected = selectedEventFromSelection(scoreDocument, selection);
    if (selected?.event?.pitch) setCursorPitch(selected.event.pitch);
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
      if (action.type === "toggle_note_input") setEditMode((current) => (current === "note_input" ? "select" : "note_input"));
      if (action.type === "input_pitch") handleInputPitch(action.step, action.chordTone);
      if (action.type === "input_rest") handleInputRest();
      if (action.type === "transpose") selection.eventIds.length ? transposeSelected(action.semitones) : applyScoreCursor(transposeCursorPitch(scoreCursor, action.semitones));
      if (action.type === "cursor_step") applyScoreCursor(moveScoreCursor(scoreDocument, scoreCursor, action.steps));
      if (action.type === "cursor_measure") applyScoreCursor(jumpScoreCursorMeasure(scoreDocument, scoreCursor, action.delta));
      if (action.type === "cursor_boundary") applyScoreCursor(jumpScoreCursorBoundary(scoreDocument, scoreCursor, action.boundary));
      if (action.type === "cursor_pitch") selection.eventIds.length ? transposeSelected(action.semitones) : applyScoreCursor(transposeCursorPitch(scoreCursor, action.semitones));
      if (action.type === "switch_staff") applyScoreCursor(switchCursorStaff(scoreCursor, action.reverse));
      if (action.type === "switch_voice") applyScoreCursor(switchCursorVoice(scoreCursor));
      if (action.type === "set_accidental") setNoteCursor((current) => ({ ...current, accidental: action.accidental }));
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
  }, [editMode, noteCursor, selection, scoreDocument, history, playbackState, scoreCursor]);

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
    const strictEntry = strictHistory.done[strictHistory.done.length - 1];
    if (strictEntry?.afterScore === scoreDocument) {
      handleStrictUndo();
      return;
    }
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
    const strictEntry = strictHistory.undone[strictHistory.undone.length - 1];
    if (strictEntry?.beforeScore === scoreDocument) {
      handleStrictRedo();
      return;
    }
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

  async function handleStrictGenerate() {
    setStrictBusy(true);
    setStatus("generating strict ScorePatch preview");
    try {
      const payload = await generateStrictScorePatchPreview(
        scoreDocument,
        instruction,
        strictScopes.targetScope,
        strictScopes.protectedScope
      ) as StrictGenerationPreview;
      setStrictGeneration(payload);
      if (payload.preview?.validation_report) setValidation(payload.preview.validation_report);
      if (payload.status === "generated") setStatus(`strict preview ${payload.preview?.validation_report.status || "ready"}`);
      else setStatus(`${payload.status}: ${payload.reason || "instruction not supported"}`);
    } catch (error: any) {
      setStrictGeneration(null);
      setStatus(`strict preview failed: ${error.message}`);
    } finally {
      setStrictBusy(false);
    }
  }

  async function handleStrictApply() {
    const patch = strictGeneration?.patch;
    if (!patch) return;
    setStrictBusy(true);
    setStatus("applying strict ScorePatch transaction");
    try {
      const beforeScore = scoreDocument;
      const payload = await applyStrictScorePatch(scoreDocument, patch);
      setValidation(payload.validation_report || {});
      if (!payload.committed) {
        setStrictGeneration((current) => current ? { ...current, preview: payload } : current);
        setStatus(payload.rollback_reason || "strict patch rolled back");
        return;
      }
      const afterScore = payload.score_document as ScoreDocument;
      setScoreDocument(afterScore);
      setStrictHistory((current) => recordStrictPatch(
        current,
        { patch, beforeScore, afterScore, validationReport: payload.validation_report }
      ));
      setDirtyMeasures(Array.from(
        { length: strictPatchRange.end_measure - strictPatchRange.start_measure + 1 },
        (_, index) => strictPatchRange.start_measure + index
      ));
      setStrictGeneration(null);
      setStatus("strict patch committed");
    } catch (error: any) {
      setStatus(`strict apply failed: ${error.message}`);
    } finally {
      setStrictBusy(false);
    }
  }

  function handleStrictReject() {
    setStrictGeneration(null);
    setStatus("strict patch rejected; canonical score unchanged");
  }

  function handleStrictUndo() {
    const result = undoStrictPatch(strictHistory, scoreDocument);
    if (!result) {
      setStatus("strict undo unavailable after intervening edits");
      return;
    }
    setScoreDocument(result.scoreDocument);
    setValidation(result.validationReport);
    setStrictGeneration(null);
    setStrictHistory(result.history);
    setStatus("strict patch undone");
  }

  function handleStrictRedo() {
    const result = redoStrictPatch(strictHistory, scoreDocument);
    if (!result) {
      setStatus("strict redo unavailable after intervening edits");
      return;
    }
    setScoreDocument(result.scoreDocument);
    setValidation(result.validationReport);
    setStrictGeneration(null);
    setStrictHistory(result.history);
    setStatus("strict patch redone");
  }

  async function handleAgentEdit(value = instruction, constraintsOverride = agentConstraints) {
    setStatus("previewing agent patch");
    try {
      const preview = await requestAgentScoreEdit(scoreDocument, value, selectedRange, constraintsOverride, {
        current_selection: selectedSummary,
        current_score_cursor: scoreCursor,
        musicality_controls: musicalityControls,
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
      let payload;
      try {
        payload = await createNotationBridgeSession(
          bridgeHost,
          musicxml,
          file.name,
          "Imported through Sera professional notation bridge"
        );
        setBridgeSession(payload.session);
      } catch {
        payload = await importMusicXmlToScoreDocument(musicxml, "Imported through Score Workbench");
        setBridgeSession(null);
      }
      setScoreDocument(payload.score_document);
      setHistory(payload.operation_history || EMPTY_OPERATION_HISTORY);
      setStrictGeneration(null);
      setStrictHistory(EMPTY_STRICT_PATCH_HISTORY);
      setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" });
      setStatus(payload.session ? `${payload.session.host_id} bridge session created` : "MusicXML imported without bridge session");
    } catch (error: any) {
      setStatus(`import failed: ${error.message}`);
    }
  }

  async function handleExportHostRevision() {
    if (!bridgeSession?.session_id) {
      setStatus("Import host-exported MusicXML before exporting a synchronized revision");
      return;
    }
    setStatus("exporting notation host revision");
    try {
      const payload = await exportNotationBridgeRevision(
        bridgeSession.session_id,
        scoreDocument,
        Number(bridgeSession.revision || 0)
      );
      setBridgeSession(payload.session);
      const fileName = String(payload.output_path || `${bridgeSession.session_id}.musicxml`).split(/[\\/]/).pop() || "sera_revision.musicxml";
      downloadTextFile(fileName, payload.musicxml);
      setValidation(payload.validation_report || {});
      setStatus(`${payload.session.host_id} revision ${payload.revision} exported`);
    } catch (error: any) {
      setStatus(`host revision export failed: ${error.message}`);
    }
  }

  async function handleOpenProject(file: File) {
    const project = migrateWorkbenchProject(JSON.parse(await file.text()));
    setScoreDocument(project.score_document);
    setHistory(project.operation_history);
    setAgentPatchHistory(project.agent_patch_history);
    setBridgeSession(null);
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

  function handleResetView() {
    setLayoutMode("fit_width");
    setZoom(layoutConfigForMode("fit_width").defaultZoom);
    setRenderNonce((current) => current + 1);
    requestAnimationFrame(() => {
      document.querySelector(".score-canvas-wrap")?.scrollTo({ left: 0, top: 0, behavior: "smooth" });
    });
    setStatus("score view reset");
  }

  function handleRerenderScore() {
    setRenderNonce((current) => current + 1);
    setStatus("score re-render requested");
  }

  function handleOpenMusicXmlTextPreview() {
    setMusicXmlPreviewOpen(true);
    setStatus("MusicXML text preview opened");
  }

  function handleInputPitch(step: string, chordTone = false) {
    const check = canInsertAtCursor(scoreDocument, noteCursor);
    if (!check.ok) {
      setNoteWarning(check.warning);
      return;
    }
    runOperation(createInsertNoteOperation(scoreDocument, noteCursor, step, chordTone));
    setCursorPitch(pitchFromStep(step, noteCursor));
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

  function handleCanvasNoteInput(preview: ClickToNotatePreview | null, chordTone: boolean) {
    if (!preview) return;
    const cursor = {
      ...noteCursor,
      measureId: preview.measureId,
      measureNumber: preview.measureNumber,
      staff: preview.staff,
      voice: preview.voice,
      offset: preview.offset,
      duration: preview.duration.replace("dotted_", "") as NoteDuration,
      dotted: preview.dotted,
      accidental: preview.accidentalMode === "none" ? "" : preview.accidentalMode,
      octave: Number(preview.pitch.match(/\d/)?.[0] || noteCursor.octave)
    };
    setNoteCursor(cursor);
    setCursorPitch(preview.pitch);
    if (!preview.valid) {
      setNoteWarning(preview.warning || "Click insertion is not valid at this location.");
      return;
    }
    const operation = createClickToNotateOperation(preview, chordTone);
    if (!operation) return;
    runOperation(operation);
    const eventId = String(operation.after.event_id || operation.target.event_id || "");
    if (eventId) setSelection(selectEvent({ ...EMPTY_SELECTION, measureIds: [preview.measureId], anchorMeasureId: preview.measureId }, eventId, preview.measureId));
    setNoteCursor((current) => advanceCursor(scoreDocument, current));
    setNoteWarning("");
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
    setCursorPitch(pitch);
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
    runOperations(generateLeftHandAccompanimentOperations(scoreDocument, selectedRange.start_measure, selectedRange.end_measure, musicalityControls.accompaniment_style === "block_chords" ? "block_chord" : "arpeggiated"), "left-hand accompaniment generated");
  }

  function applyScoreCursor(cursor: ScoreCursor) {
    setCursorSnap(cursor.snap);
    setCursorPitch(cursor.pitch);
    setNoteCursor((current) => noteInputFromScoreCursor(cursor, current));
    setStatus(`cursor M${cursor.measure_number} beat ${cursor.beat.toFixed(2)} ${cursor.staff} voice ${cursor.voice}`);
  }

  function handleCursorMove(target: HitTarget | null, point: { x: number; y: number }) {
    const next = scoreCursorFromHit(scoreDocument, scoreCursor, target, point);
    if (next) applyScoreCursor(next);
  }

  function applyMusicalityTool(toolInstruction: string) {
    setInstruction(toolInstruction);
    handleAgentEdit(toolInstruction, { ...agentConstraints, musicality_controls: musicalityControls, current_score_cursor: scoreCursor });
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
        canRedo={history.undone.length > 0 || Boolean(strictHistory.undone.length && strictHistory.undone[strictHistory.undone.length - 1].beforeScore === scoreDocument)}
        canUndo={history.done.length > 0 || Boolean(strictHistory.done.length && strictHistory.done[strictHistory.done.length - 1].afterScore === scoreDocument)}
        dotted={noteCursor.dotted}
        duration={noteCursor.duration}
        editMode={editMode}
        loop={playbackState.loop}
        layoutMode={layoutMode}
        onAccidental={(accidental) => setNoteCursor((current) => ({ ...current, accidental: accidental as NoteInputCursor["accidental"] }))}
        onDotted={() => setNoteCursor((current) => ({ ...current, dotted: !current.dotted }))}
        onDuration={(duration: NoteDuration) => setNoteCursor((current) => ({ ...current, duration, dotted: duration.startsWith("dotted_") }))}
        onEditMode={setEditMode}
        onExportMidi={handleExportMidi}
        onExportMusicXml={handleExportMusicXml}
        onExportPdf={handleExportPdf}
        onFitWidth={() => setZoom(1)}
        onImport={handleImport}
        onLayoutMode={setLayoutMode}
        onLoop={(loop) => setPlaybackState((current) => ({ ...current, loop }))}
        onNew={() => { setScoreDocument(createEmptyScoreDocument(8)); setBridgeSession(null); setSelection({ ...EMPTY_SELECTION, measureIds: ["m1"], anchorMeasureId: "m1" }); }}
        onOpenMusicXmlTextPreview={handleOpenMusicXmlTextPreview}
        onOpen={handleOpenProject}
        onPlay={handlePlay}
        onRedo={handleRedo}
        onRerender={handleRerenderScore}
        onRendererMode={(mode) => setRendererMode(mode as RendererMode)}
        onResetView={handleResetView}
        onSave={handleSaveProject}
        onSlur={slurSelected}
        onStaff={(staff) => { setNoteCursor((current) => ({ ...current, staff })); setCursorPitch(staff === "left_hand" ? "C3" : "C4"); }}
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
      <div className="workbench-metadata-strip">
        <strong>{scoreDocument.title || "Untitled Sera Score"}</strong>
        <span>{scoreDocument.composer || "Sera"}</span>
        <span>{scoreDocument.global.key}</span>
      </div>
      <section className="workbench-panel notation-bridge-panel">
        <div>
          <strong>{t("notationBridge.title")}</strong>
          <p>{t("notationBridge.importHint")}</p>
        </div>
        <label>
          {t("notationBridge.host")}
          <select disabled={Boolean(bridgeSession)} onChange={(event) => setBridgeHost(event.target.value)} value={bridgeHost}>
            {(notationHosts.length ? notationHosts : [
              { host_id: "musescore", display_name: "MuseScore Studio" },
              { host_id: "sibelius", display_name: "Avid Sibelius Ultimate" },
              { host_id: "musicxml", display_name: "Generic MusicXML" }
            ]).map((host) => (
              <option key={host.host_id} value={host.host_id}>{host.display_name}</option>
            ))}
          </select>
        </label>
        <div className="notation-bridge-status">
          <span>{t("notationBridge.session")}: {bridgeSession?.session_id || t("notationBridge.notConnected")}</span>
          <span>{t("notationBridge.revision")}: {bridgeSession?.revision ?? 0}</span>
          <span>{bridgeSession ? t("notationBridge.fileReady") : t("notationBridge.directPending")}</span>
        </div>
        <button disabled={!bridgeSession} onClick={handleExportHostRevision} type="button">
          {t("notationBridge.exportRevision")}
        </button>
      </section>
      <LocationBar
        cursor={scoreCursor}
        clickPreview={clickPreview}
        hoverText={hoverText(scoreDocument, hoverTarget, t)}
        selectionText={selectionText(selectedSummary, t)}
        validationState={validation?.errors?.length ? "error" : validation?.warnings?.length ? "warning" : "ok"}
      />
      {autosaveProject && (
        <section className="autosave-banner">
          <strong>{t("autosave.found")}</strong>
          <button onClick={() => { const project = migrateWorkbenchProject(autosaveProject); setScoreDocument(project.score_document); setHistory(project.operation_history); setAgentPatchHistory(project.agent_patch_history); setAutosaveProject(null); }} type="button">{t("autosave.recover")}</button>
          <button onClick={() => { clearAutosave(); setAutosaveProject(null); }} type="button">{t("autosave.discard")}</button>
        </section>
      )}
      {musicXmlPreviewOpen && (
        <section className="workbench-panel musicxml-preview-panel">
          <div className="panel-title-row">
            <h2>{t("workbench.musicxmlPreview")}</h2>
            <button onClick={() => setMusicXmlPreviewOpen(false)} type="button">{t("workbench.close")}</button>
          </div>
          <pre>{scoreDocumentToSimpleMusicXml(scoreDocument)}</pre>
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
            <h3>{t("workbench.linesAndStaff")}</h3>
            <div className="palette-grid">
              <button onClick={tieSelected} type="button">{t("workbench.tie")}</button>
              <button onClick={slurSelected} type="button">{t("workbench.slur")}</button>
              <button onClick={() => runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "update_staff", { staff: "left_hand" })), "moved to left hand")} type="button">{t("workbench.toLeftHand")}</button>
              <button onClick={() => runOperations(selection.eventIds.map((eventId) => operationForSelectedEvent(eventId, "update_staff", { staff: "right_hand" })), "moved to right hand")} type="button">{t("workbench.toRightHand")}</button>
              <button onClick={generateAccompaniment} type="button">{t("workbench.generateLeftHand")}</button>
            </div>
          </section>
          <KeyboardShortcutsHelp />
          <MusicalityControlPanel controls={musicalityControls} onApplyTool={applyMusicalityTool} onChange={setMusicalityControls} />
        </aside>
        <main className="workbench-center">
          <ScoreCanvas
            clickPreview={clickPreview}
            cursorSnap={cursorSnap}
            editMode={editMode}
            hoverEventId={hoverEventId}
            hoverTarget={hoverTarget}
            inputTool={tool}
            layoutMode={layoutMode}
            noteInputCursor={noteCursor}
            onClearSelection={() => setSelection(clearSelection())}
            onClickPreview={setClickPreview}
            onCursorMove={handleCursorMove}
            onDragEdit={(eventIds, deltaY, deltaX, duplicate) => runOperations(buildDragOperations(scoreDocument, eventIds, deltaY, deltaX, duplicate), "drag edit applied")}
            onHitDebug={setHitDebug}
            onHoverEvent={setHoverEventId}
            onHoverTarget={setHoverTarget}
            onNoteInput={handleCanvasNoteInput}
            onRenderStatus={setRendererStatus}
            onSelectAll={() => setSelection(selectAllMeasures(scoreDocument))}
            onSelectEvent={(eventId, measureId, additive) => setSelection((current) => selectEvent(current, eventId, measureId, additive))}
            onSelectMeasure={(measureId, additive, rangeSelect) => setSelection((current) => rangeSelect ? selectMeasureRange(scoreDocument, current.anchorMeasureId || current.measureIds[0] || measureId, measureId) : selectMeasure(current, measureId, additive))}
            onSelectTargets={(targets) => setSelection(selectTargets(targets))}
            patchRange={agentWorkflow === "strict" && strictGeneration?.patch ? strictPatchRange : patchPreview?.patch?.target_range}
            playbackMeasure={playbackState.currentMeasure}
            rendererMode={rendererMode}
            renderNonce={renderNonce}
            scoreDocument={scoreDocument}
            scoreCursor={scoreCursor}
            selectedEventIds={selection.eventIds}
            selectedMeasureIds={selection.measureIds}
            showBeatGrid={showBeatGrid}
            showHitBoxes={showHitBoxes}
            validationWarnings={validation?.warnings || []}
            zoom={zoom}
          />
          {agentWorkflow === "strict" && <StrictScoreComparison generation={strictGeneration} />}
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
            <h2>{t("workbench.hitMapping")}</h2>
            <label className="inline-check">
              <input checked={showHitBoxes} onChange={(event) => setShowHitBoxes(event.target.checked)} type="checkbox" />
              {t("workbench.showHitBoxes")}
            </label>
            <label className="inline-check">
              <input checked={showBeatGrid} onChange={(event) => setShowBeatGrid(event.target.checked)} type="checkbox" />
              {t("workbench.showBeatGrid")}
            </label>
            <label>
              {t("workbench.location.snap")}
              <select value={cursorSnap} onChange={(event) => setCursorSnap(event.target.value as ScoreCursorSnap)}>
                <option value="beat">{formatMusicTerm("beat", t)}</option>
                <option value="eighth">{formatMusicTerm("eighth", t)}</option>
                <option value="sixteenth">{formatMusicTerm("sixteenth", t)}</option>
                <option value="triplet">{formatMusicTerm("triplet", t)}</option>
              </select>
            </label>
            <pre>{JSON.stringify({ selected: selectedSummary, hitDebug, dirtyMeasures }, null, 2)}</pre>
          </section>
          <section className="workbench-panel workflow-switcher">
            <div className="panel-heading tight">
              <h2>Agent workflow</h2>
              <span>Local Electron</span>
            </div>
            <div className="toolbar-row">
              <button className={agentWorkflow === "strict" ? "active" : ""} onClick={() => setAgentWorkflow("strict")} type="button">
                Strict ScorePatch
              </button>
              <button className={agentWorkflow === "legacy" ? "active" : ""} onClick={() => setAgentWorkflow("legacy")} type="button">
                Legacy compatible
              </button>
            </div>
          </section>
          {agentWorkflow === "strict" ? (
            <SeraEditResearchPanel
              busy={strictBusy}
              canRedo={Boolean(strictHistory.undone.length && strictHistory.undone[strictHistory.undone.length - 1].beforeScore === scoreDocument)}
              canUndo={Boolean(strictHistory.done.length && strictHistory.done[strictHistory.done.length - 1].afterScore === scoreDocument)}
              generation={strictGeneration}
              instruction={instruction}
              onApply={handleStrictApply}
              onGenerate={handleStrictGenerate}
              onRedo={handleStrictRedo}
              onReject={handleStrictReject}
              onTargetStaffChange={(value) => setAgentConstraints((current) => ({ ...current, target_staff: value }))}
              onTargetVoiceChange={(value) => setAgentConstraints((current) => ({ ...current, target_voice: value }))}
              onUndo={handleStrictUndo}
              protectedScope={strictScopes.protectedScope}
              setInstruction={setInstruction}
              targetScope={strictScopes.targetScope}
              targetStaff={agentConstraints.target_staff}
              targetVoice={agentConstraints.target_voice}
            />
          ) : (
            <>
              <AgentEditPanel
                constraints={agentConstraints}
                currentLocation={scoreCursor}
                disabled={status.includes("previewing")}
                instruction={instruction}
                onAgentEdit={handleAgentEdit}
                onConstraintsChange={setAgentConstraints}
                onExplain={handleExplainSelection}
                selectedRange={selectedRange}
                setInstruction={setInstruction}
              />
              <PatchPreviewPanel onAccept={handleAcceptPatch} onPartialApply={handlePartialPatch} onRegenerate={() => handleAgentEdit()} onReject={handleRejectPatch} preview={patchPreview} />
            </>
          )}
          {explanation && (
            <section className="workbench-panel">
              <h2>{t("workbench.selectionExplanation")}</h2>
              <p>{explanation.summary}</p>
              <p>{explanation.harmony_analysis}</p>
              <p>{explanation.melodic_analysis}</p>
              <p>{explanation.rhythmic_analysis}</p>
            </section>
          )}
          <section className="workbench-panel">
            <h2>{t("mode.validation")}</h2>
            <button onClick={refreshValidation} type="button">{t("workbench.runValidator")}</button>
            <pre>{JSON.stringify(validation || {}, null, 2)}</pre>
          </section>
        </aside>
      </div>
      <ScoreStatusBar cursor={scoreCursor} history={history} hoverTarget={hoverTarget} layoutMode={layoutMode} rendererStatus={rendererStatus} scoreDocument={scoreDocument} status={`${status}; playback M${playbackState.currentMeasure || "-"}; recent ops ${recentOperations.length}`} zoom={zoom} />
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

function selectedEventFromSelection(score: ScoreDocument, selection: { measureIds: string[]; eventIds: string[] }) {
  for (const measure of score.measures) {
    const event = measure.events.find((item) => selection.eventIds.includes(item.event_id));
    if (event) return { measure, event };
  }
  return null;
}

function scoreCursorFromHit(score: ScoreDocument, current: ScoreCursor, target: HitTarget | null, point: { x: number; y: number }): ScoreCursor | null {
  if (!target?.measureId) return null;
  const measure = score.measures.find((item) => item.measure_id === target.measureId) || score.measures.find((item) => item.number === target.measureNumber);
  if (!measure) return null;
  if (target.type === "event" && target.eventId) {
    const event = measure.events.find((item) => item.event_id === target.eventId);
    if (event) {
      return validateScoreCursor(score, {
        ...current,
        measure_id: measure.measure_id,
        measure_number: measure.number,
        staff: event.staff === "left_hand" ? "left_hand" : "right_hand",
        voice: event.voice === 2 ? 2 : 1,
        offset: Number(event.offset || 0),
        duration: event.duration as ScoreCursor["duration"],
        pitch: event.pitch || (event.staff === "left_hand" ? "C3" : "C4")
      });
    }
  }
  return validateScoreCursor(score, {
    ...current,
    measure_id: measure.measure_id,
    measure_number: measure.number,
    staff: target.staff === "left_hand" ? "left_hand" : "right_hand",
    voice: target.voice === 2 ? 2 : 1,
    offset: typeof target.offset === "number" ? target.offset : current.offset,
    pitch: target.pitch || pitchFromCanvasPoint(point.y, target.staff === "left_hand" ? "left_hand" : "right_hand")
  });
}

function hoverText(score: ScoreDocument, target: HitTarget | null, t?: Translate) {
  if (!target) return "";
  if (target.type === "event" && target.eventId) {
    const found = findEvent(score, target.eventId);
    if (!found) return target.fallbackReason || "";
    const eventType = t ? formatMusicTerm(found.event.type, t) : found.event.type;
    const duration = t ? formatDuration(found.event.duration, t) : found.event.duration;
    const staff = t ? formatMusicTerm(found.event.staff, t) : found.event.staff;
    return `${eventType} ${found.event.pitch || (t ? formatMusicTerm("rest", t) : "rest")} ${duration} M${found.measure.number} ${t ? formatMusicTerm("beat", t) : "beat"} ${(Number(found.event.offset || 0) + 1).toFixed(2)} ${staff} V${found.event.voice}`;
  }
  return `${t ? formatMusicTerm("measure", t) : "measure"} ${target.measureNumber} ${t ? formatMusicTerm("beat", t) : "beat"} ${Number(target.beat || 1).toFixed(2)} ${target.staff && t ? formatMusicTerm(target.staff, t) : target.staff || ""} V${target.voice || 1}`;
}

function selectionText(summary: Record<string, any>, t?: Translate) {
  if (summary.event_count) return `${summary.event_count} ${t ? formatMusicTerm("event", t) : "events"} / ${summary.note_count} ${t ? formatMusicTerm("note", t) : "notes"}`;
  if (summary.measure_count) return `${summary.measure_count} ${t ? formatMusicTerm("measure", t) : "measures"}`;
  return t ? t("workbench.none") : "none";
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
