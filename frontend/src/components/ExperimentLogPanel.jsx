import { useI18n } from "../i18n/useI18n";
import { formatMusicTerm } from "../i18n/musicTerms";
import { asArray, asObject, displayValue } from "./componentDataGuards.js";

export default function ExperimentLogPanel({ experiments, selectedRunId }) {
  const { t } = useI18n();
  const records = asArray(experiments).filter((record) => record && typeof record === "object");

  return (
    <section className="panel log-panel">
      <div className="panel-heading">
        <h2>{t("log.title")}</h2>
        <span>{records.length}</span>
      </div>
      <div className="log-list">
        {records.map((record) => {
          const intent = asObject(record.intent);
          const validation = asObject(record.validation);
          const style = intent.style ? formatMusicTerm(displayValue(intent.style), t) : `${t("field.style")} ${t("common.pending")}`;
          const key = intent.key ? formatMusicTerm(displayValue(intent.key), t) : `${t("field.key")} ${t("common.pending")}`;
          const meter = displayValue(intent.meter || intent.time_signature) || `${t("field.meter")} ${t("common.pending")}`;
          const measureCount = intent.length_measures ?? intent.bars ?? validation.metrics?.measure_count ?? 0;
          const runId = displayValue(record.run_id) || `run-${records.indexOf(record)}`;

          return (
            <article className={record.run_id === selectedRunId ? "log-row selected" : "log-row"} key={runId}>
              <strong>{runId}</strong>
              <span>{style}{" \u00b7 "}{key}</span>
              <small>
                {meter}{" \u00b7 "}{displayValue(measureCount)} {t("workbench.status.measures")}
                {record.user_rating?.average_score ? ` \u00b7 ${t("common.rating")} ${record.user_rating.average_score}` : ""}
              </small>
            </article>
          );
        })}
        {!records.length && <div className="muted-row">{t("log.noRuns")}</div>}
      </div>
    </section>
  );
}
