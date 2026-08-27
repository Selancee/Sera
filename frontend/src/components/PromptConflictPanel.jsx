import { useI18n } from "../i18n/useI18n";
import { asArray, displayValue } from "./componentDataGuards.js";

export default function PromptConflictPanel({ resolution }) {
  const { t } = useI18n();
  const conflicts = asArray(resolution?.conflicts).filter((conflict) => conflict && typeof conflict === "object");
  const warnings = asArray(resolution?.warnings).map(displayValue);
  if (!conflicts.length && !warnings.length) return null;
  return (
    <section className="panel prompt-conflict-panel" data-testid="prompt-conflict-panel">
      <div className="panel-heading">
        <h2>{t("promptConflict.title")}</h2>
        <span>{t("promptConflict.count", { count: conflicts.length })}</span>
      </div>
      {warnings.map((warning) => (
        <p className="source-warning" key={warning}>{warning}</p>
      ))}
      <div className="conflict-list">
        {conflicts.map((conflict, index) => (
          <article key={`${conflict.field}-${index}`}>
            <strong>{displayValue(conflict.field)}</strong>
            <span>{t("promptConflict.prompt")}: {displayValue(conflict.prompt_value)}</span>
            <span>{t("promptConflict.ui")}: {displayValue(conflict.ui_value)} ({displayValue(conflict.ui_source) || "unknown"})</span>
            <em>{displayValue(conflict.resolution)}</em>
          </article>
        ))}
      </div>
    </section>
  );
}
