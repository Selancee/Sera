function formatValue(value) {
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") {
    const controls = [
      value.rhythmic_density,
      value.melodic_contour,
      value.cadence,
      value.motif_strategy
    ].filter(Boolean);
    return controls.length ? controls.join(" / ") : JSON.stringify(value);
  }
  return value ?? "";
}

const PLAN_KEYS = [
  "title",
  "style",
  "mood",
  "instrumentation",
  "key",
  "meter",
  "tempo",
  "length_measures",
  "form",
  "texture",
  "difficulty",
  "musical_controls"
];

export default function AgentPlanPanel({ compact = false, result }) {
  const planJson = result?.plan?.agent_plan_json || {};
  const measures = result?.plan?.measures || [];
  const schema = result?.plan?.schema_validation;
  const sectionPlan = planJson.section_plan || [];

  return (
    <section className={compact ? "panel compact-plan" : "panel plan-panel"}>
      <div className="panel-heading">
        <h2>Agent Plan</h2>
        <span>{schema?.valid ? "schema valid" : result ? "schema review" : "pending"}</span>
      </div>

      <div className="intent-grid">
        {PLAN_KEYS.map((key) => (
          <div className="intent-item" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{formatValue(planJson[key])}</strong>
          </div>
        ))}
      </div>

      {!compact && (
        <>
          <div className="section-plan">
            {sectionPlan.map((section) => (
              <article key={`${section.section}-${section.measures}`}>
                <strong>{section.section}</strong>
                <span>{section.measures}</span>
                <p>{section.description}</p>
              </article>
            ))}
          </div>

          <div className="measure-table" role="table" aria-label="Measure-level plan">
            <div className="measure-row head" role="row">
              <span>Bar</span>
              <span>Section</span>
              <span>Chord</span>
              <span>Density</span>
              <span>Contour</span>
              <span>Cadence</span>
            </div>
            {measures.map((measure) => (
              <div className="measure-row" key={measure.index} role="row">
                <span>{measure.index}</span>
                <span>{measure.section}</span>
                <span>{measure.chord}</span>
                <span>{measure.rhythmic_density || measure.density}</span>
                <span>{measure.melodic_contour || "-"}</span>
                <span>{measure.cadence || "-"}</span>
              </div>
            ))}
          </div>

          <details className="json-details">
            <summary>Full Agent plan JSON</summary>
            <pre>{JSON.stringify(planJson, null, 2)}</pre>
          </details>
        </>
      )}
    </section>
  );
}
