import { useI18n } from "../i18n/useI18n";
import { asArray, displayValue } from "./componentDataGuards.js";

export default function ConsistencyReportPanel({ report }) {
  const { t } = useI18n();
  if (!report) return null;
  const mismatchCount = Number(report.mismatch_count || 0);
  const warnings = asArray(report.warnings).map(displayValue);
  const errors = asArray(report.errors).map(displayValue);
  return (
    <section className={`panel consistency-panel ${mismatchCount || errors.length ? "warning" : "ok"}`}>
      <div className="panel-heading">
        <h2>{t("score.consistencyReport")}</h2>
        <span>{mismatchCount || errors.length ? t("common.review") : t("common.passed")}</span>
      </div>
      <div className="consistency-grid">
        <Metric label="MusicXML events" value={report.musicxml_event_count} />
        <Metric label="ScoreDocument events" value={report.score_document_event_count} />
        <Metric label="MIDI events" value={report.midi_event_count} />
        <Metric label="Mismatches" value={report.mismatch_count} />
      </div>
      {(warnings.length > 0 || errors.length > 0) && (
        <ul className="consistency-list">
          {[...errors, ...warnings].slice(0, 6).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{displayValue(value ?? 0)}</strong>
    </div>
  );
}
