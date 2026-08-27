import { useI18n } from "../i18n/useI18n";
import { asArray, displayValue } from "./componentDataGuards.js";

export default function ResolvedGenerationRequestPanel({ resolution }) {
  const { t } = useI18n();
  if (!resolution) return null;
  const terms = asArray(resolution.prompt_terms);
  return (
    <section className="panel resolved-request-panel" data-testid="resolved-generation-request-panel">
      <div className="panel-heading">
        <h2>{t("resolvedRequest.title")}</h2>
        <span>{t("resolvedRequest.alignment", { score: resolution.prompt_plan_alignment_score ?? "-" })}</span>
      </div>
      <div className="intent-grid">
        <div className="intent-item">
          <span>{t("resolvedRequest.rawPrompt")}</span>
          <strong>{displayValue(resolution.raw_prompt) || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>{t("resolvedRequest.sourceTerms")}</span>
          <strong>{asArray(resolution.source_prompt_terms).map(displayValue).join(", ") || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>{t("resolvedRequest.unparsedTerms")}</span>
          <strong>{asArray(resolution.unparsed_prompt_terms).map(displayValue).join(", ") || t("common.none")}</strong>
        </div>
        <div className="intent-item">
          <span>{t("resolvedRequest.defaultsUsed")}</span>
          <strong>{asArray(resolution.defaults_used).map(displayValue).join(", ") || t("common.none")}</strong>
        </div>
      </div>
      <details className="json-details">
        <summary>{t("resolvedRequest.promptTermsAndControls")}</summary>
        <pre>{JSON.stringify({ terms, resolved_controls: resolution.resolved_controls, ui_controls: resolution.ui_controls }, null, 2)}</pre>
      </details>
    </section>
  );
}
