import { getExportUrl } from "../api.js";

const FORMATS = [
  ["musicxml", "MusicXML"],
  ["midi", "MIDI"],
  ["pdf", "PDF"],
  ["plan", "JSON Plan"],
  ["validation_report", "Validation"],
  ["experiment_log", "Experiment Log"]
];

export default function ExportPanel({ onEvaluate, result }) {
  const runId = result?.run_id;

  return (
    <section className="panel export-panel">
      <div className="panel-heading">
        <h2>Export</h2>
        <span>{runId ? "ready" : "pending"}</span>
      </div>
      <div className="export-grid">
        {FORMATS.map(([format, label]) => (
          <a
            className={runId ? "export-link" : "export-link disabled"}
            href={runId ? getExportUrl(runId, format) : undefined}
            key={format}
          >
            {label}
          </a>
        ))}
      </div>
      <button className="secondary-action" disabled={!runId} onClick={onEvaluate} type="button">
        Evaluate
      </button>
    </section>
  );
}
