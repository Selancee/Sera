import { useEffect, useMemo, useRef, useState } from "react";
import { createDragPreview, type DragPreview } from "../score/dragEditing";
import { scoreDocumentToSimpleMusicXml } from "../score/musicxmlAdapter";
import { createRenderer, primaryRendererForMode } from "../score/renderers/rendererFactory";
import { hitTestMarquee, hitTestPoint } from "../score/renderers/hitTesting";
import { buildOverlayHitMap, eventX, LEFT_STAFF_TOP, MEASURE_WIDTH, pitchToStaffY, SCORE_LEFT, STAFF_TOP } from "../score/renderers/layoutMapping";
import type { HitTarget, LayoutBox, RendererMode, RendererStatus } from "../score/renderers/renderTypes";
import type { ScoreDocument, ScoreEvent } from "../score/scoreTypes";

type Props = {
  scoreDocument: ScoreDocument;
  selectedEventIds: string[];
  selectedMeasureIds: string[];
  hoverEventId: string;
  playbackMeasure: number;
  patchRange?: { start_measure: number; end_measure: number };
  validationWarnings: string[];
  zoom: number;
  rendererMode: RendererMode;
  editMode: "select" | "note_input";
  showHitBoxes?: boolean;
  onSelectEvent: (eventId: string, measureId: string, additive?: boolean) => void;
  onSelectMeasure: (measureId: string, additive?: boolean, rangeSelect?: boolean) => void;
  onSelectTargets: (targets: HitTarget[]) => void;
  onHoverEvent: (eventId: string) => void;
  onClearSelection: () => void;
  onSelectAll: () => void;
  onRenderStatus: (status: RendererStatus) => void;
  onHitDebug: (debug: Record<string, unknown>) => void;
  onNoteInput: (target: HitTarget | null, point: { x: number; y: number }, chordTone: boolean) => void;
  onDragEdit: (eventIds: string[], deltaY: number, deltaX: number, duplicate: boolean) => void;
};

export default function ScoreCanvas(props: Props) {
  const width = Math.max(920, props.scoreDocument.measures.length * MEASURE_WIDTH + 80);
  const height = 230;
  const svgRef = useRef<SVGSVGElement | null>(null);
  const osmdRef = useRef<HTMLDivElement | null>(null);
  const [activeRenderer, setActiveRenderer] = useState<RendererMode>("fallback");
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragHit, setDragHit] = useState<HitTarget | null>(null);
  const [dragRect, setDragRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [dragPreview, setDragPreview] = useState<DragPreview | null>(null);
  const hitMap = useMemo(() => buildOverlayHitMap(props.scoreDocument, activeRenderer === "osmd" ? "osmd" : "fallback"), [props.scoreDocument, activeRenderer]);
  const layoutBoxes = hitMap.boxes;
  const warningMeasures = useMemo(
    () =>
      new Set(
        props.validationWarnings.flatMap((warning) => {
          const match = warning.match(/Measure\s+(\d+)/i);
          return match ? [Number(match[1])] : [];
        })
      ),
    [props.validationWarnings]
  );

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
          zoom: props.zoom
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
  }, [props.scoreDocument, props.rendererMode, props.zoom]);

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
    const hit = hitTestPoint(layoutBoxes, point.x, point.y);
    setDragHit(hit);
    setDragStart(point);
    setDragRect(null);
    setDragPreview(null);
    props.onHitDebug({ ...(hitMap.debug || {}), last_hit: hit });
  }

  function handleMouseMove(event: React.MouseEvent<SVGSVGElement>) {
    if (!dragStart) return;
    const point = pointer(event);
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
      const hit = hitTestPoint(layoutBoxes, point.x, point.y);
      props.onHitDebug({ ...(hitMap.debug || {}), last_hit: hit });
      if (props.editMode === "note_input") {
        props.onNoteInput(hit, point, event.shiftKey);
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

  return (
    <div className="score-canvas-wrap" style={{ ["--zoom" as string]: props.zoom }}>
      <div className={activeRenderer === "osmd" ? "osmd-score-layer active" : "osmd-score-layer"} ref={osmdRef} />
      <svg
        className={`workbench-score-svg ${activeRenderer === "osmd" ? "overlay" : ""}`}
        onMouseDown={handleMouseDown}
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
        {props.showHitBoxes && <HitBoxOverlay boxes={layoutBoxes} />}
        {dragRect && <rect className="selection-marquee" height={dragRect.height} width={dragRect.width} x={dragRect.x} y={dragRect.y} />}
        {dragPreview && <DragPreviewSvg preview={dragPreview} />}
      </svg>
    </div>
  );
}

function FallbackScoreSvg({
  scoreDocument,
  selectedEventIds,
  selectedMeasureIds,
  hoverEventId,
  playbackMeasure,
  patchRange,
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
  warningMeasures: Set<number>;
  width: number;
  height: number;
  onSelectEvent: (eventId: string, measureId: string, additive?: boolean) => void;
  onSelectMeasure: (measureId: string, additive?: boolean, rangeSelect?: boolean) => void;
  onHoverEvent: (eventId: string) => void;
}) {
  return (
    <>
      <rect className="paper-bg" height={height} width={width} x="0" y="0" />
      {[0, 1, 2, 3, 4].map((line) => (
        <line key={`r${line}`} x1="32" x2={width - 32} y1={STAFF_TOP + line * 9} y2={STAFF_TOP + line * 9} />
      ))}
      {[0, 1, 2, 3, 4].map((line) => (
        <line key={`l${line}`} x1="32" x2={width - 32} y1={LEFT_STAFF_TOP + line * 9} y2={LEFT_STAFF_TOP + line * 9} />
      ))}
      {scoreDocument.measures.map((measure, index) => {
        const x = index * MEASURE_WIDTH + SCORE_LEFT;
        const selected = selectedMeasureIds.includes(measure.measure_id);
        const inPatch = patchRange && measure.number >= patchRange.start_measure && measure.number <= patchRange.end_measure;
        return (
          <g key={measure.measure_id} onClick={(event) => onSelectMeasure(measure.measure_id, event.ctrlKey || event.metaKey, event.shiftKey)} onContextMenu={(event) => { event.preventDefault(); onSelectMeasure(measure.measure_id); }} onDoubleClick={() => onSelectMeasure(measure.measure_id)}>
            <rect
              className={`measure-hit ${selected ? "selected" : ""} ${inPatch ? "patch-range" : ""} ${warningMeasures.has(measure.number) ? "warning" : ""} ${playbackMeasure === measure.number ? "playing" : ""}`}
              height="152"
              width={MEASURE_WIDTH - 10}
              x={x - 4}
              y="42"
            />
            <line className="barline" x1={x} x2={x} y1={STAFF_TOP} y2={LEFT_STAFF_TOP + 36} />
            <text className="measure-number" x={x + 8} y="35">{measure.number}</text>
            <text className="section-label" x={x + 34} y="35">{measure.section}</text>
            <text className="harmony-label" x={x + 8} y="208">{measure.harmony}</text>
            {inPatch && <text className="ai-badge" x={x + 78} y="35">AI</text>}
            {measure.events.map((event, eventIndex) => (
              <WorkbenchNote
                event={event}
                hovered={hoverEventId === event.event_id}
                index={eventIndex}
                key={event.event_id}
                measureId={measure.measure_id}
                measureX={x}
                onHover={onHoverEvent}
                onSelect={onSelectEvent}
                selected={selectedEventIds.includes(event.event_id)}
              />
            ))}
          </g>
        );
      })}
      <line className="barline" x1={scoreDocument.measures.length * MEASURE_WIDTH + SCORE_LEFT} x2={scoreDocument.measures.length * MEASURE_WIDTH + SCORE_LEFT} y1={STAFF_TOP} y2={LEFT_STAFF_TOP + 36} />
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

function WorkbenchNote({ event, index, measureX, measureId, selected, hovered, onSelect, onHover }: { event: ScoreEvent; index: number; measureX: number; measureId: string; selected: boolean; hovered: boolean; onSelect: (eventId: string, measureId: string, additive?: boolean) => void; onHover: (eventId: string) => void }) {
  const x = eventX(measureX, event, index);
  const y = event.staff === "left_hand" ? LEFT_STAFF_TOP + 22 : pitchToStaffY(event);
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
