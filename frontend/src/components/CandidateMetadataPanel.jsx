function metricRows(report) {
  const metrics = report?.selected_candidate_metrics || report?.metrics || {};
  return Object.entries(metrics).filter(([, value]) => value !== undefined && value !== null);
}

export default function CandidateMetadataPanel({ metadata }) {
  const candidate = metadata?.candidate_generation || metadata?.generation_metadata?.candidate_generation || {};
  const rank = metadata?.candidate_rank_report || metadata?.generation_metadata?.candidate_rank_report || {};
  if (!candidate?.candidate_count) return null;
  const rejected = Array.isArray(candidate.rejected_candidates) ? candidate.rejected_candidates : [];
  const diversity = candidate.candidate_actual_diversity || {};
  return (
    <details className="panel compact-report" open>
      <summary>Candidate generation</summary>
      <div className="research-grid">
        <div className="intent-item">
          <span>run seed</span>
          <strong>{candidate.run_seed || "-"}</strong>
        </div>
        <div className="intent-item">
          <span>selected</span>
          <strong>{candidate.selected_candidate_index ?? "-"}</strong>
        </div>
        <div className="intent-item">
          <span>count</span>
          <strong>{candidate.candidate_count}</strong>
        </div>
        <div className="intent-item">
          <span>score</span>
          <strong>{candidate.selected_candidate_score ?? rank.score ?? "-"}</strong>
        </div>
      </div>
      {Object.keys(diversity).length > 0 && (
        <div className="research-grid">
          {Object.entries(diversity).map(([key, value]) => (
            <div className="intent-item" key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>{String(value)}</strong>
            </div>
          ))}
        </div>
      )}
      <div className="research-grid">
        {metricRows(candidate).map(([key, value]) => (
          <div className="intent-item" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{String(value)}</strong>
          </div>
        ))}
      </div>
      {rejected.length > 0 && (
        <ul className="compact-list">
          {rejected.map((item) => (
            <li key={item.candidate_index}>
              #{item.candidate_index}: {item.score} - {(item.rejection_reasons || []).join(", ")}
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}
