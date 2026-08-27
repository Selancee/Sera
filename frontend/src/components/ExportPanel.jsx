import { getExportUrl } from "../api.js";
import { useI18n } from "../i18n/useI18n";

const FORMATS = [
  ["musicxml", "MusicXML"],
  ["midi", "MIDI"],
  ["pdf", "PDF"],
  ["plan", "JSON Plan"],
  ["validation_report", "export.validation"],
  ["experiment_log", "export.experimentLog"]
];

export default function ExportPanel({ onEvaluate, result }) {
  const { t } = useI18n();
  const runId = result?.run_id;

  return (
    <section className="panel export-panel">
      <div className="panel-heading">
        <h2>{t("export.title")}</h2>
        <span>{runId ? t("common.ready") : t("common.pending")}</span>
      </div>
      <div className="export-grid">
        {FORMATS.map(([format, label]) => (
          <a
            className={runId ? "export-link" : "export-link disabled"}
            href={runId ? getExportUrl(runId, format) : undefined}
            key={format}
          >
            {label.includes(".") ? t(label) : label}
          </a>
        ))}
      </div>
      <button className="secondary-action" disabled={!runId} onClick={onEvaluate} type="button">
        {t("export.evaluate")}
      </button>
    </section>
  );
}
