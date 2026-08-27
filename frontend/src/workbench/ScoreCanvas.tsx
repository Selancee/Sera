import { useEffect, useMemo, useRef, useState } from "react";
import { buildClickToNotatePreview, type ClickToNotatePreview } from "../score/clickToNotate";
import { createDragPreview, type DragPreview } from "../score/dragEditing";
import { hitTestWithAreas } from "../score/hitAreas";
import { type ScoreLayoutMode } from "../score/layoutConfig";
import { scoreDocumentToSimpleMusicXml } from "../score/musicxmlAdapter";
import type { NoteInputCursor } from "../score/noteInput";
import { createRenderer, primaryRendererForMode } from "../score/renderers/rendererFactory";
import { hitTestMarquee } from "../score/renderers/hitTesting";
import { buildOverlayHitMap, eventX, LEFT_STAFF_TOP, pitchToStaffY, STAFF_TOP } from "../score/renderers/layoutMapping";
import type { HitTarget, LayoutBox, RendererMode, RendererStatus } from "../score/renderers/renderTypes";
import type { ScoreCursor, ScoreCursorSnap } from "../score/scoreCursor";
import type { ScoreDocument, ScoreEvent } from "../score/scoreTypes";
import { buildSystemLayout, measureLayoutAt } from "../score/systemLayout";
import BeatGridOverlay from "./BeatGridOverlay";
import ClickPreviewOverlay from "./ClickPreviewOverlay";
import HitAreaOverlay from "./HitAreaOverlay";
import ScoreCursorOverlay from "./ScoreCursorOverlay";
import StaffLaneOverlay from "./StaffLaneOverlay";

type Props = {
  scoreDocument: ScoreDocument;
  selectedEventIds: string[];
  selectedMeasureIds: string[];
  hoverEventId: string;
  hoverTarget: HitTarget | null;
  playbackMeasure: number;
  patchRange?: { start_measure: number; end_measure: number };
  validationWarnings: Array<string | { message?: unknown; details?: Record<string, unknown> }>;
  zoom: number;
  layoutMode: ScoreLayoutMode;
  renderNonce: number;
  rendererMode: RendererMode;
  editMode: "select" | "note_input";
  showHitBoxes?: boolean;
  showBeatGrid?: boolean;
  scoreCursor: ScoreCursor;
  cursorSnap: ScoreCursorSnap;
  noteInputCursor: NoteInputCursor;
  inputTool: string;
  clickPreview: ClickToNotatePreview | null;
  onSelectEvent: (eventId: string, measureId: string, additive?: boolean) => void;
  onSelectMeasure: (measureId: string, additive?: boolean, rangeSelect?: boolean) => void;
  onSelectTargets: (targets: HitTarget[]) => void;
  onHoverEvent: (eventId: string) => void;
  onHoverTarget: (target: HitTarget | null) => void;
  onClickPreview: (preview: ClickToNotatePreview | null) => void;
  onCursorMove: (target: HitTarget | null, point: { x: number; y: number }) => void;
  onClearSelection: () => void;
  onSelectAll: () => void;
  onRenderStatus: (status: RendererStatus) => void;
  onHitDebug: (debug: Record<string, unknown>) => void;
  onNoteInput: (preview: ClickToNotatePreview | null, chordTone: boolean) => void;
  onDragEdit: (eventIds: string[], deltaY: number, deltaX: number, duplicate: boolean) => void;
};

export default function ScoreCanvas(props: Props) {
  const systemLayout = useMemo(() => buildSystemLayout(props.scoreDocument.measures.length, props.layoutMode), [props.scoreDocument.measures.length, props.layoutMode]);
  const width = systemLayout.width;
  const height = systemLayout.height;
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const osmdRef = useRef<HTMLDivElement | null>(null);
  const [activeRenderer, setActiveRenderer] = useState<RendererMode>("fallback");
  const [containerWidth, setContainerWidth] = useState(0);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragHit, setDragHit] = useState<HitTarget | null>(null);
  const [dragRect, setDragRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [dragPreview, setDragPreview] = useState<DragPreview | null>(null);
  const hitMap = useMemo(() => buildOverlayHitMap(props.scoreDocument, activeRenderer === "osmd" ? "osmd" : "fallback", props.layoutMode), [props.scoreDocument, activeRenderer, props.layoutMode]);
  const layoutBoxes = hitMap.boxes;
  const effectiveZoom = useMemo(() => {
    if (props.layoutMode !== "fit_width" || !containerWidth) return props.zoom;
    const fitZoom = (containerWidth - 44) / Math.max(1, width);
    return clamp(fitZoom * props.zoom, 0.2, 1.2);
  }, [containerWidth, props.layoutMode, props.zoom, width]);
  const warningMeasures = useMemo(
    () =>
      new Set(
        props.validationWarnings.flatMap((warning) => {
          const text = validationWarningText(warning);
          const match = text.match(/(?:Measure|小节)\s*(\d+)/i);
          return match ? [Number(match[1])] : [];
        })
      ),
    [props.validationWarnings]
  );

  useEffect(() => {
    const target = wrapRef.current;
    if (!target) return;
    const update = () => setContainerWidth(Math.round(target.clientWidth));
    update();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }
    const observer = new ResizeObserver(update);
    observer.observe(target);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function renderExternal() {
      const requested = primaryRendererForMode(props.rendererMode);
      if (requested === "fallback") {
        setActiveRenderer("fallback");
        props.onRenderStatus({ requestedMode: props.rendererMode, activeMode: "fallback", state: "ready", message: "SVG fallback renderer active", renderMs: 0 });
        return;
      }
      if (!osmdRef.current) return;
      const started = performance.now();
      props.onRenderStatus({ requestedMode: props.rendererMode, activeMode: requested, state: "loading", message: "rendering score", renderMs: 0 });
      try {
        const renderer = createRenderer(requested);
        const result = await renderer.render(osmdRef.current, {
          scoreDocument: props.scoreDocument,
          musicxml: scoreDocumentToSimpleMusicXml(props.scoreDocument),
          zoom: effectiveZoom,
          layoutMode: props.layoutMode
        });
        if (cancelled) return;
        const active = result.activeMode === "osmd" ? "osmd" : "fallback";
        setActiveRenderer(active);
        props.onRenderStatus({ ...result, requestedMode: props.rendererMode, activeMode: active, renderMs: result.renderMs || Math.round(performance.now() - started) });
        props.onHitDebug(result.mappingDebug || hitMap.debug);
        if ((result.renderMs || 0) > 3000) {
          props.onRenderStatus({ ...result, requestedMode: props.rendererMode, activeMode: active, state: "ready", message: `${result.message}; render exceeded 3s`, renderMs: result.renderMs });
        }
      } catch (error: any) {
        if (cancelled) return;
        setActiveRenderer("fallback");
        props.onHitDebug({ ...hitMap.debug, fallbackReason: error.message || String(error) });
        props.onRenderStatus({
          requestedMode: props.rendererMode,
          activeMode: "fallback",
          state: props.rendererMode === "osmd" ? "error" : "fallback",
          message: `Renderer fallback: ${error.message || error}`,
          renderMs: Math.round(performance.now() - started)
        });
      }
    }
    renderExternal();
    return () => {
      cancelled = true;
    };
  }, [props.scoreDocument, props.rendererMode, effectiveZoom, props.layoutMode, props.renderNonce]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") props.onClearSelection();
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "a") {
        event.preventDefault();
        props.onSelectAll();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [props]);

  function pointer(event: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const transformed = point.matrixTransform(svg.getScreenCTM()?.inverse());
    return { x: transformed.x, y: transformed.y };
  }

  function handleMouseDown(event: React.MouseEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    const point = pointer(event);
    const hit = hitTestWithAreas(props.scoreDocument, layoutBoxes, point, props.cursorSnap, props.scoreCursor.voice);
    setDragHit(hit);
    setDragStart(point);
    setDragRect(null);
    setDragPreview(null);
    props.onHitDebug({ ...(hitMap.debug || {}), last_hit: hit });
  }

  function handleMouseMove(event: React.MouseEvent<SVGSVGElement>) {
    const point = pointer(event);
    if (!dragStart) {
      const hit = hitTestWithAreas(props.scoreDocument, layoutBoxes, point, props.cursorSnap, props.scoreCursor.voice);
      props.onHoverTarget(hit);
      props.onHoverEvent(hit?.type === "event" && hit.eventId ? hit.eventId : "");
      props.onClickPreview(previewFor(hit, point));
      return;
    }
    const dx = point.x - dragStart.x;
    const dy = point.y - dragStart.y;
    if (dragHit?.type === "event" && Math.hypot(dx, dy) > 6) {
      const ids = props.selectedEventIds.includes(String(dragHit.eventId)) ? props.selectedEventIds : [String(dragHit.eventId)];
      setDragPreview(createDragPreview(props.scoreDocument, ids, dy, dx));
      setDragRect(null);
      return;
    }
    setDragRect({
      x: Math.min(point.x, dragStart.x),
      y: Math.min(point.y, dragStart.y),
      width: Math.abs(point.x - dragStart.x),
      height: Math.abs(point.y - dragStart.y)
    });
  }

  function handleMouseUp(event: React.MouseEvent<SVGSVGElement>) {
    const point = pointer(event);
    const dx = dragStart ? point.x - dragStart.x : 0;
    const dy = dragStart ? point.y - dragStart.y : 0;
    if (dragPreview && dragHit?.type === "event") {
      const ids = props.selectedEventIds.includes(String(dragHit.eventId)) ? props.selectedEventIds : [String(dragHit.eventId)];
      props.onDragEdit(ids, dy, dx, event.altKey);
      setDragPreview(null);
      setDragStart(null);
      setDragHit(null);
      return;
    }
    if (dragRect && dragRect.width > 8 && dragRect.height > 8) {
      const hits = hitTestMarquee(layoutBoxes, dragRect);
      props.onSelectTargets(hits);
    } else {
      const hit = hitTestWithAreas(props.scoreDocument, layoutBoxes, point, props.cursorSnap, props.scoreCursor.voice);
      props.onHitDebug({ ...(hitMap.debug || {}), last_hit: hit });
      props.onCursorMove(hit, point);
      if (props.editMode === "note_input") {
        props.onNoteInput(previewFor(hit, point, event.shiftKey), event.shiftKey);
      } else if (hit?.type === "event" && hit.eventId) {
        props.onSelectEvent(hit.eventId, hit.measureId, event.ctrlKey || event.metaKey || event.shiftKey);
      } else if (hit?.type === "measure") {
        props.onSelectMeasure(hit.measureId, event.ctrlKey || event.metaKey, event.shiftKey);
      }
    }
    setDragStart(null);
    setDragHit(null);
    setDragRect(null);
  }

  function handleMouseLeave() {
    if (dragStart) return;
    props.onHoverTarget(null);
    props.onHoverEvent("");
    props.onClickPreview(null);
  }

  function previewFor(hit: HitTarget | null, point: { x: number; y: number }, chordTone = false) {
    return buildClickToNotatePreview({
      score: props.scoreDocument,
      cursor: props.scoreCursor,
      hitTarget: hit,
      point,
      boxes: layoutBoxes,
      snap: props.cursorSnap,
      inputMode: props.editMode === "note_input" ? (props.inputTool === "rest" ? "rest_input" : "note_input") : "select",
      duration: props.noteInputCursor.duration,
      dotted: props.noteInputCursor.dotted,
      accidentalMode: props.noteInputCursor.accidental,
      chordTone
    });
  }

  return (
    <div className={`score-canvas-wrap layout-${props.layoutMode}`} ref={wrapRef} style={{ ["--zoom" as string]: effectiveZoom, ["--score-width" as string]: `${width}px` }}>
      <div className={activeRenderer === "osmd" ? "osmd-score-layer active" : "osmd-score-layer"} ref={osmdRef} />
      <svg
        className={`workbench-score-svg ${activeRenderer === "osmd" ? "overlay" : ""}`}
        onMouseDown={handleMouseDown}
        onMouseLeave={handleMouseLeave}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        ref={svgRef}
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        {activeRenderer !== "osmd" && (
          <FallbackScoreSvg
            height={height}
            onHoverEvent={props.onHoverEvent}
            onSelectEvent={props.onSelectEvent}
            onSelectMeasure={props.onSelectMeasure}
            patchRange={props.patchRange}
            playbackMeasure={props.playbackMeasure}
            scoreDocument={props.scoreDocument}
            selectedEventIds={props.selectedEventIds}
            selectedMeasureIds={props.selectedMeasureIds}
            hoverEventId={props.hoverEventId}
            layoutMode={props.layoutMode}
            warningMeasures={warningMeasures}
            width={width}
          />
        )}
        {activeRenderer === "osmd" && (
          <OverlayHitRegions
            boxes={layoutBoxes}
            onSelectMeasure={props.onSelectMeasure}
            patchRange={props.patchRange}
            playbackMeasure={props.playbackMeasure}
            scoreDocument={props.scoreDocument}
            selectedMeasureIds={props.selectedMeasureIds}
            warningMeasures={warningMeasures}
          />
        )}
        <StaffLaneOverlay activeStaff={props.scoreCursor.staff} boxes={layoutBoxes} />
        <BeatGridOverlay boxes={layoutBoxes} scoreDocument={props.scoreDocument} snap={props.cursorSnap} visible={props.showBeatGrid} />
        <ScoreCursorOverlay boxes={layoutBoxes} cursor={props.scoreCursor} scoreDocument={props.scoreDocument} />
        <ClickPreviewOverlay boxes={layoutBoxes} preview={props.clickPreview} scoreDocument={props.scoreDocument} visible={props.editMode === "note_input"} />
        <HitAreaOverlay boxes={layoutBoxes} hoverTarget={props.hoverTarget || dragHit} scoreDocument={props.scoreDocument} visible={props.showHitBoxes} />
        {props.showHitBoxes && <HitBoxOverlay boxes={layoutBoxes} />}
        {dragRect && <rect className="selection-marquee" height={dragRect.height} width={dragRect.width} x={dragRect.x} y={dragRect.y} />}
        {dragPreview && <DragPreviewSvg preview={dragPreview} />}
      </svg>
    </div>
  );
}

export function validationWarningText(warning: string | { message?: unknown }) {
  if (typeof warning === "string") return warning;
  return typeof warning?.message === "string" ? warning.message : "";
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function FallbackScoreSvg({
  scoreDocument,
  selectedEventIds,
  selectedMeasureIds,
  hoverEventId,
  playbackMeasure,
  patchRange,
  layoutMode,
  warningMeasures,
  width,
  height,
  onSelectEvent,
  onSelectMeasure,
  onHoverEvent
}: {
  scoreDocument: ScoreDocument;
  selectedEventIds: string[];
  selectedMeasureIds: string[];
  hoverEventId: string;
  playbackMeasure: number;
  patchRange?: { start_measure: number; end_measure: number };
  layoutMode: ScoreLayoutMode;
  warningMeasures: Set<number>;
  width: number;
  height: number;
  onSelectEvent: (eventId: string, measureId: string, additive?: boolean) => void;
  onSelectMeasure: (measureId: string, additive?: boolean, rangeSelect?: boolean) => void;
  onHoverEvent: (eventId: string) => void;
}) {
  const layout = buildSystemLayout(scoreDocument.measures.length, layoutMode);
  return (
    <>
      <rect className="paper-bg" height={height} width={width} x="0" y="0" />
      {layout.systems.map((system) => (
        <g key={`system-${system.index}`}>
          {[0, 1, 2, 3, 4].map((line) => (
            <line key={`r${system.index}-${line}`} x1="32" x2={width - 32} y1={system.y + STAFF_TOP + line * 9} y2={system.y + STAFF_TOP + line * 9} />
          ))}
          {[0, 1, 2, 3, 4].map((line) => (
            <line key={`l${system.index}-${line}`} x1="32" x2={width - 32} y1={system.y + LEFT_STAFF_TOP + line * 9} y2={system.y + LEFT_STAFF_TOP + line * 9} />
          ))}
        </g>
      ))}
      {scoreDocument.measures.map((measure, index) => {
        const measureLayout = measureLayoutAt(layout, index);
        const x = measureLayout.x;
        const top = measureLayout.y;
        const selected = selectedMeasureIds.includes(measure.measure_id);
        const inPatch = patchRange && measure.number >= patchRange.start_measure && measure.number <= patchRange.end_measure;
        return (
          <g key={measure.measure_id} onClick={(event) => onSelectMeasure(measure.measure_id, event.ctrlKey || event.metaKey, event.shiftKey)} onContextMenu={(event) => { event.preventDefault(); onSelectMeasure(measure.measure_id); }} onDoubleClick={() => onSelectMeasure(measure.measure_id)}>
            <rect
              className={`measure-hit ${selected ? "selected" : ""} ${inPatch ? "patch-range" : ""} ${warningMeasures.has(measure.number) ? "warning" : ""} ${playbackMeasure === measure.number ? "playing" : ""}`}
              height="176"
              width={measureLayout.width}
              x={x}
              y={top + 42}
            />
            <line className="barline" x1={x} x2={x} y1={top + STAFF_TOP} y2={top + LEFT_STAFF_TOP + 36} />
            <text className="measure-number" x={x + 8} y={top + 35}>{measure.number}</text>
            <text className="section-label" x={x + 34} y={top + 35}>{measure.section}</text>
            <text className="harmony-label" x={x + 8} y={top + LEFT_STAFF_TOP + 62}>{measure.harmony}</text>
            {inPatch && <text className="ai-badge" x={x + 78} y={top + 35}>AI</text>}
            {measure.events.map((event, eventIndex) => (
              <WorkbenchNote
                event={event}
                hovered={hoverEventId === event.event_id}
                index={eventIndex}
                key={event.event_id}
                measureId={measure.measure_id}
                measureX={x}
                systemY={top}
                onHover={onHoverEvent}
                onSelect={onSelectEvent}
                selected={selectedEventIds.includes(event.event_id)}
              />
            ))}
          </g>
        );
      })}
      {layout.systems.map((system) => {
        const lastIndex = system.measureIndexes[system.measureIndexes.length - 1];
        const last = measureLayoutAt(layout, lastIndex);
        return <line className="barline" key={`end-${system.index}`} x1={last.x + last.width} x2={last.x + last.width} y1={system.y + STAFF_TOP} y2={system.y + LEFT_STAFF_TOP + 36} />;
      })}
    </>
  );
}

function HitBoxOverlay({ boxes }: { boxes: LayoutBox[] }) {
  return (
    <g className="hit-box-debug">
      {boxes.filter((box) => box.type === "event").map((box) => (
        <rect height={box.height} key={`${box.measureId}-${box.eventId}`} width={box.width} x={box.x} y={box.y} />
      ))}
    </g>
  );
}

function DragPreviewSvg({ preview }: { preview: DragPreview }) {
  return (
    <g className="drag-preview-svg">
      <text x="48" y="24">
        {preview.semitones > 0 ? "+" : ""}{preview.semitones} st / offset {preview.offsetDelta > 0 ? "+" : ""}{preview.offsetDelta}
      </text>
    </g>
  );
}

function OverlayHitRegions({
  boxes,
  selectedMeasureIds,
  patchRange,
  playbackMeasure,
  warningMeasures,
  onSelectMeasure
}: {
  boxes: LayoutBox[];
  selectedMeasureIds: string[];
  scoreDocument: ScoreDocument;
  patchRange?: { start_measure: number; end_measure: number };
  playbackMeasure: number;
  warningMeasures: Set<number>;
  onSelectMeasure: (measureId: string, additive?: boolean, rangeSelect?: boolean) => void;
}) {
  return (
    <>
      {boxes.filter((box) => box.type === "measure").map((box) => {
        const selected = selectedMeasureIds.includes(box.measureId);
        const inPatch = patchRange && box.measureNumber >= patchRange.start_measure && box.measureNumber <= patchRange.end_measure;
        return (
          <rect
            className={`measure-hit osmd-overlay ${selected ? "selected" : ""} ${inPatch ? "patch-range" : ""} ${warningMeasures.has(box.measureNumber) ? "warning" : ""} ${playbackMeasure === box.measureNumber ? "playing" : ""}`}
            height={box.height}
            key={box.measureId}
            onClick={(event) => onSelectMeasure(box.measureId, event.ctrlKey || event.metaKey, event.shiftKey)}
            width={box.width}
            x={box.x}
            y={box.y}
          />
        );
      })}
    </>
  );
}

function WorkbenchNote({ event, index, measureX, measureId, systemY, selected, hovered, onSelect, onHover }: { event: ScoreEvent; index: number; measureX: number; measureId: string; systemY: number; selected: boolean; hovered: boolean; onSelect: (eventId: string, measureId: string, additive?: boolean) => void; onHover: (eventId: string) => void }) {
  const x = eventX(measureX, event, index);
  const y = event.staff === "left_hand" ? systemY + LEFT_STAFF_TOP + 22 : pitchToStaffY(event, systemY + STAFF_TOP);
  const className = `workbench-note ${selected ? "selected" : ""} ${hovered ? "hovered" : ""} ${event.type === "rest" ? "rest" : ""}`;
  return (
    <g className={className} onClick={(eventClick) => { eventClick.stopPropagation(); onSelect(event.event_id, measureId, eventClick.ctrlKey || eventClick.metaKey); }} onContextMenu={(eventClick) => { eventClick.preventDefault(); onSelect(event.event_id, measureId); }} onMouseEnter={() => onHover(event.event_id)} onMouseLeave={() => onHover("")}>
      {event.type === "rest" ? (
        <rect height="8" rx="2" width="14" x={x - 7} y={y - 4} />
      ) : (
        <>
          <ellipse cx={x} cy={y} rx="7" ry="5" transform={`rotate(-18 ${x} ${y})`} />
          <line x1={x + 6} x2={x + 6} y1={y} y2={y - 30} />
        </>
      )}
      <text x={x - 10} y={y + 22}>{event.duration.slice(0, 1)}</text>
    </g>
  );
}
