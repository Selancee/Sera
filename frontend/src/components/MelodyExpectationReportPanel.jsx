export default function MelodyExpectationReportPanel({ report, metadata }) {
  if (!report || Object.keys(report).length === 0) return null;
  const phraseScores = metadata?.phrase_melody?.phrase_level_scores || {};
  const rows = [
    ["source", metadata?.melody_generation_source],
    ["phrase contour", phraseScores.phrase_contour_score],
    ["motif development", phraseScores.motif_development_score],
    ["target tones", phraseScores.target_tone_hit_score],
    ["mechanical penalty", phraseScores.mechanical_template_penalty],
    ["candidate count", metadata?.melody_candidate_count],
    ["selected melody", metadata?.selected_melody_candidate_index],
    ["score", report.melody_expectation_score],
    ["leap reversal", report.leap_reversal_rate],
    ["mean regression", report.mean_regression_score],
    ["gap fill", report.gap_fill_score],
    ["closure", report.closure_score],
    ["tritones", report.unresolved_tritone_count],
    ["dissonances", report.unresolved_dissonance_count]
  ];
  return (
    <details className="panel compact-report">
      <summary>Melody expectation</summary>
      <div className="research-grid">
        {rows.map(([label, value]) => (
          <div className="intent-item" key={label}>
            <span>{label}</span>
            <strong>{value ?? "-"}</strong>
          </div>
        ))}
      </div>
    </details>
  );
}
