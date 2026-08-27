import { asArray, asObject } from "./componentDataGuards.js";

export default function MelodyLineReportPanel({ report, crossMeasureReport }) {
  const data = asObject(report);
  const primary = asObject(data.primary_melody);
  const cross = asObject(crossMeasureReport);
  const excluded = asArray(data.excluded_lines);
  if (!Object.keys(data).length && !Object.keys(cross).length) return null;
  return (
    <section className="panel melody-line-report-panel">
      <div className="panel-heading">
        <h2>Melody Line</h2>
        <span>{cross.valid === false ? "review" : "primary"}</span>
      </div>
      <p className="metadata-ok">Melody diagnostics are computed from the extracted primary melody line, not from mixed playback events.</p>
      <div className="metadata-editor-grid">
        <Info label="Primary staff" value={primary.staff || "right_hand"} />
        <Info label="Primary voice" value={primary.voice || 1} />
        <Info label="Melody notes" value={asArray(primary.events).length} />
        <Info label="Excluded lines" value={excluded.length} />
        <Info label="Tritone rate" value={cross.cross_measure_tritone_rate ?? "-"} />
        <Info label="Large leaps" value={cross.cross_measure_large_leap_count ?? "-"} />
        <Info label="Unresolved leaps" value={cross.unresolved_cross_measure_leap_count ?? "-"} />
        <Info label="Max interval" value={cross.max_cross_measure_interval ?? "-"} />
      </div>
      {excluded.length > 0 && (
        <ul className="compact-list">
          {excluded.map((line, index) => (
            <li key={`${line.staff}-${line.voice}-${index}`}>{line.staff} voice {line.voice}: {line.reason}</li>
          ))}
        </ul>
      )}
      {asArray(cross.repairs_applied).length > 0 && (
        <details className="json-details">
          <summary>Repairs applied</summary>
          <pre>{JSON.stringify(cross.repairs_applied, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}

function Info({ label, value }) {
  return (
    <div className="metadata-info-item">
      <span>{label}</span>
      <strong>{String(value ?? "-")}</strong>
    </div>
  );
}
