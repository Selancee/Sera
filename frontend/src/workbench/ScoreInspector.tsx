import type { ScoreDocument, ScoreEvent, ScoreMeasure, ScoreOperation } from "../score/scoreTypes";

type Props = {
  scoreDocument: ScoreDocument;
  selectedEventId: string;
  selectedMeasureId: string;
  onOperation: (operation: ScoreOperation) => void;
};

export default function ScoreInspector({ scoreDocument, selectedEventId, selectedMeasureId, onOperation }: Props) {
  const measure = scoreDocument.measures.find((item) => item.measure_id === selectedMeasureId) || scoreDocument.measures[0];
  const event = measure?.events.find((item) => item.event_id === selectedEventId);
  return (
    <section className="workbench-panel">
      <h2>Score Inspector</h2>
      <GlobalControls scoreDocument={scoreDocument} onOperation={onOperation} />
      {event ? (
        <EventControls event={event} measure={measure} onOperation={onOperation} />
      ) : (
        <MeasureControls measure={measure} onOperation={onOperation} />
      )}
    </section>
  );
}

function GlobalControls({ scoreDocument, onOperation }: { scoreDocument: ScoreDocument; onOperation: (operation: ScoreOperation) => void }) {
  return (
    <div className="inspector-grid">
      <label>
        Key
        <input
          value={scoreDocument.global.key}
          onChange={(event) => onOperation({ source: "user", type: "change_key", target: {}, after: { key: event.target.value }, description: "Change key" })}
        />
      </label>
      <label>
        Meter
        <select
          value={scoreDocument.global.meter}
          onChange={(event) => onOperation({ source: "user", type: "change_meter", target: {}, after: { meter: event.target.value }, description: "Change meter" })}
        >
          {["4/4", "3/4", "6/8"].map((meter) => <option key={meter}>{meter}</option>)}
        </select>
      </label>
      <label>
        Tempo
        <input
          min="40"
          max="220"
          type="number"
          value={scoreDocument.global.tempo}
          onChange={(event) => onOperation({ source: "user", type: "change_tempo", target: {}, after: { tempo: Number(event.target.value) }, description: "Change tempo" })}
        />
      </label>
    </div>
  );
}

function EventControls({ event, measure, onOperation }: { event: ScoreEvent; measure: ScoreMeasure; onOperation: (operation: ScoreOperation) => void }) {
  return (
    <div className="inspector-grid">
      <span>Measure {measure.number}</span>
      <label>
        Pitch
        <input value={event.pitch} onChange={(change) => onOperation({ source: "user", type: "update_pitch", target: { measure_id: measure.measure_id, event_id: event.event_id }, after: { pitch: change.target.value }, description: "Update pitch" })} />
      </label>
      <label>
        Duration
        <select value={event.duration} onChange={(change) => onOperation({ source: "user", type: "update_duration", target: { measure_id: measure.measure_id, event_id: event.event_id }, after: { duration: change.target.value }, description: "Update duration" })}>
          {["whole", "half", "quarter", "eighth", "sixteenth", "dotted_quarter", "dotted_eighth"].map((duration) => <option key={duration}>{duration}</option>)}
        </select>
      </label>
      <label>
        Dynamic
        <select value={event.dynamic} onChange={(change) => onOperation({ source: "user", type: "change_dynamic", target: { measure_id: measure.measure_id, event_id: event.event_id }, after: { dynamic: change.target.value }, description: "Change dynamic" })}>
          {["p", "mp", "mf", "f"].map((dynamic) => <option key={dynamic}>{dynamic}</option>)}
        </select>
      </label>
      <label>
        Staff
        <select value={event.staff} onChange={(change) => onOperation({ source: "user", type: "update_staff", target: { measure_id: measure.measure_id, event_id: event.event_id }, after: { staff: change.target.value }, description: "Move staff" })}>
          <option value="right_hand">right hand</option>
          <option value="left_hand">left hand</option>
        </select>
      </label>
    </div>
  );
}

function MeasureControls({ measure, onOperation }: { measure: ScoreMeasure; onOperation: (operation: ScoreOperation) => void }) {
  if (!measure) return <span>No measure selected.</span>;
  return (
    <div className="inspector-grid">
      <span>Measure {measure.number}</span>
      <label>
        Section
        <input value={measure.section} onChange={(change) => onOperation({ source: "user", type: "add_section_label", target: { measure_id: measure.measure_id }, after: { section: change.target.value }, description: "Change section label" })} />
      </label>
      <label>
        Harmony
        <input value={measure.harmony} onChange={(change) => onOperation({ source: "user", type: "add_harmony_label", target: { measure_id: measure.measure_id }, after: { harmony: change.target.value }, description: "Change harmony label" })} />
      </label>
      <label>
        Cadence
        <select value={measure.cadence} onChange={(change) => onOperation({ source: "user", type: "add_cadence", target: { measure: measure.number, start_measure: measure.number, end_measure: measure.number }, after: { cadence: change.target.value }, description: "Change cadence" })}>
          {["none", "half", "authentic"].map((cadence) => <option key={cadence}>{cadence}</option>)}
        </select>
      </label>
      <button onClick={() => onOperation({ source: "user", type: "simplify_rhythm", target: { start_measure: measure.number, end_measure: measure.number }, after: { duration: "quarter" }, description: "Simplify measure" })} type="button">Simplify</button>
      <button onClick={() => onOperation({ source: "user", type: "humanize_rhythm", target: { start_measure: measure.number, end_measure: measure.number }, after: { duration: "eighth" }, description: "Increase rhythmic density" })} type="button">More density</button>
    </div>
  );
}

