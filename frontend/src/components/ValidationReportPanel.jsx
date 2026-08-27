import { useI18n } from "../i18n/useI18n";
import { formatFieldLabel } from "../i18n/musicTerms";
import { asArray, asObject, displayValue } from "./componentDataGuards.js";

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
  return displayValue(value) || "pending";
}

export default function ValidationReportPanel({ detailed = false, result }) {
  const { t } = useI18n();
  const report = asObject(result?.validation_report);
  const notationReport = asObject(result?.generation_metadata?.notation_validation_report || result?.metadata?.notation_validation_report);
  const normalizationReport = asObject(result?.generation_metadata?.notation_normalization_report || result?.metadata?.notation_normalization_report);
  const warnings = asArray(report.warnings).map(displayValue);
  const errors = asArray(report.errors).map(displayValue);

  return (
    <section className={detailed ? "panel validation-panel detailed" : "panel validation-panel"}>
      <div className="panel-heading">
        <h2>{t("validation.title")}</h2>
        <span>{result ? (errors.length ? t("validation.needsReview") : t("common.passed")) : t("common.pending")}</span>
      </div>
      <div className="validation-grid">
        {REPORT_KEYS.map((key) => (
          <div className="validation-item" key={key}>
            <span>{formatFieldLabel(key, t)}</span>
            <strong>{formatMetric(report[key])}</strong>
          </div>
        ))}
      </div>
      {notationReport.valid != null && (
        <div className="validation-grid notation-validation-grid">
          {[
            ["notation.valid", notationReport.valid],
            ["notation.measureDuration", notationReport.measure_duration_valid],
            ["notation.restGrouping", notationReport.rest_grouping_valid],
            ["notation.dottedDuration", notationReport.dotted_duration_valid],
            ["notation.tie", notationReport.tie_valid],
            ["notation.fixes", normalizationReport.report?.duration_fixes || normalizationReport.report?.rest_grouping_fixes || 0]
          ].map(([key, value]) => (
            <div className="validation-item" key={key}>
              <span>{String(key).replace("notation.", "").replace(/([A-Z])/g, " $1")}</span>
              <strong>{formatMetric(value)}</strong>
            </div>
          ))}
        </div>
      )}
      {(detailed || warnings.length || errors.length) && (
        <div className="validation-messages">
          <strong>{t("validation.warnings")}</strong>
          {warnings.length ? warnings.map((warning) => <p key={warning}>{warning}</p>) : <p>{t("common.none")}</p>}
          <strong>{t("validation.errors")}</strong>
          {errors.length ? errors.map((error) => <p key={error}>{error}</p>) : <p>{t("common.none")}</p>}
        </div>
      )}
    </section>
  );
}
