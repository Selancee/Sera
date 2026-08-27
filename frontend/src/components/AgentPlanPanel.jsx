import { useI18n } from "../i18n/useI18n";
import { formatFieldLabel, formatMusicTerm } from "../i18n/musicTerms";
import { asArray, asObject, displayValue } from "./componentDataGuards.js";

function formatValue(value, t) {
  if (Array.isArray(value)) return value.map((item) => formatMusicTerm(displayValue(item), t)).join(", ");
  if (value && typeof value === "object") {
    const controls = [
      value.rhythmic_density,
      value.melodic_contour,
      value.cadence,
      value.motif_strategy,
      value.texture,
      value.accompaniment_style,
      value.harmony_flavor
    ].filter(Boolean);
    return controls.length ? controls.map((item) => formatMusicTerm(displayValue(item), t)).join(" / ") : displayValue(value);
  }
  return typeof value === "string" ? formatMusicTerm(value, t) : displayValue(value);
}

const PLAN_KEYS = [
  "title",
  "style",
  "base_style",
  "custom_style_tags",
  "mood",
  "instrumentation",
  "key",
  "meter",
  "tempo",
  "length_measures",
  "form",
  "texture",
  "difficulty",
  "musical_controls",
  "style_profile",
  "source_prompt_terms",
  "unparsed_prompt_terms",
  "prompt_plan_alignment_score"
];

export default function AgentPlanPanel({ compact = false, result }) {
  const { t } = useI18n();
  const planJson = asObject(result?.plan?.agent_plan_json);
  const measures = asArray(result?.plan?.measures).filter((measure) => measure && typeof measure === "object");
  const schema = result?.plan?.schema_validation;
  const sectionPlan = asArray(planJson.section_plan).filter((section) => section && typeof section === "object");
  const grounding = asArray(planJson.plan_grounding ?? result?.plan?.global_plan?.plan_grounding).filter(
    (item) => item && typeof item === "object"
  );

  return (
    <section className={compact ? "panel compact-plan" : "panel plan-panel"}>
      <div className="panel-heading">
        <h2>{t("plan.title")}</h2>
        <span>{schema?.valid ? t("plan.schemaValid") : result ? t("plan.schemaReview") : t("common.pending")}</span>
      </div>

      <div className="intent-grid">
        {PLAN_KEYS.map((key) => (
          <div className="intent-item" key={key}>
            <span>{formatFieldLabel(key, t)}</span>
            <strong>{formatValue(planJson[key], t)}</strong>
          </div>
        ))}
      </div>

      {!compact && (
        <>
          <div className="section-plan">
            {sectionPlan.map((section) => (
              <article key={`${section.section}-${section.measures}`}>
                <strong>{displayValue(section.section)}</strong>
                <span>{displayValue(section.measures)}</span>
                <p>{displayValue(section.description)}</p>
              </article>
            ))}
          </div>

          {grounding.length > 0 && (
            <div className="grounding-list" data-testid="plan-grounding-list">
              {grounding.map((item, index) => (
                <article key={`${item.decision}-${index}`}>
                  <strong>{displayValue(item.decision)}</strong>
                  <span>{displayValue(item.source)}</span>
                  <p>{asArray(item.source_prompt_terms).map(displayValue).join(", ") || "default"}</p>
                </article>
              ))}
            </div>
          )}

          <div className="measure-table" role="table" aria-label={t("plan.measureTable")}>
            <div className="measure-row head" role="row">
              <span>{t("plan.bar")}</span>
              <span>{t("plan.section")}</span>
              <span>{t("plan.chord")}</span>
              <span>{t("plan.density")}</span>
              <span>{t("plan.contour")}</span>
              <span>{t("plan.cadence")}</span>
            </div>
            {measures.map((measure) => (
              <div className="measure-row" key={measure.index ?? displayValue(measure)} role="row">
                <span>{displayValue(measure.index)}</span>
                <span>{displayValue(measure.section)}</span>
                <span>{displayValue(measure.chord)}</span>
                <span>{formatMusicTerm(displayValue(measure.rhythmic_density || measure.density || "-"), t)}</span>
                <span>{formatMusicTerm(displayValue(measure.melodic_contour || "-"), t)}</span>
                <span>{formatMusicTerm(displayValue(measure.cadence || "-"), t)}</span>
              </div>
            ))}
          </div>

          <details className="json-details">
            <summary>{t("plan.fullJson")}</summary>
            <pre>{JSON.stringify(planJson, null, 2)}</pre>
          </details>
        </>
      )}
    </section>
  );
}
