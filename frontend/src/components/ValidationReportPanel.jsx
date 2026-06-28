const REPORT_KEYS = [
  "valid_musicxml",
  "measure_count_match",
  "bar_completeness_score",
  "pitch_range_valid",
  "empty_measure_count",
  "midi_export_success",
  "pdf_export_success"
];

function formatMetric(value) {
  if (typeof value === "number") return Number.isInteger(value) ? value : value.toFixed(2);
  if (typeof value === "boolean") return value ? "yes" : "no";
  return value ?? "pending";
}

export default function ValidationReportPanel({ detailed = false, result }) {
  const report = result?.validation_report || {};
  const warnings = report.warnings || [];
  const errors = report.errors || [];

  return (
    <section className={detailed ? "panel validation-panel detailed" : "panel validation-panel"}>
      <div className="panel-heading">
        <h2>Validation Report</h2>
        <span>{result ? (errors.length ? "needs review" : "passed") : "pending"}</span>
      </div>
      <div className="validation-grid">
        {REPORT_KEYS.map((key) => (
          <div className="validation-item" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{formatMetric(report[key])}</strong>
          </div>
        ))}
      </div>
      {(detailed || warnings.length || errors.length) && (
        <div className="validation-messages">
          <strong>Warnings</strong>
          {warnings.length ? warnings.map((warning) => <p key={warning}>{warning}</p>) : <p>None</p>}
          <strong>Errors</strong>
          {errors.length ? errors.map((error) => <p key={error}>{error}</p>) : <p>None</p>}
        </div>
      )}
    </section>
  );
}
