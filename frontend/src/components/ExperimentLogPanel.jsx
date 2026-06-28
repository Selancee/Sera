export default function ExperimentLogPanel({ experiments, selectedRunId }) {
  return (
    <section className="panel log-panel">
      <div className="panel-heading">
        <h2>Experiment Log</h2>
        <span>{experiments.length}</span>
      </div>
      <div className="log-list">
        {experiments.map((record) => (
          <article className={record.run_id === selectedRunId ? "log-row selected" : "log-row"} key={record.run_id}>
            <strong>{record.run_id}</strong>
            <span>{record.intent?.style || "style pending"} · {record.intent?.key || "key pending"}</span>
            <small>
              {record.intent?.meter || record.intent?.time_signature || "meter"} ·{" "}
              {record.intent?.length_measures ?? record.intent?.bars ?? record.validation?.metrics?.measure_count ?? 0} measures
              {record.user_rating?.average_score ? ` · rating ${record.user_rating.average_score}` : ""}
            </small>
          </article>
        ))}
        {!experiments.length && <div className="muted-row">No runs yet</div>}
      </div>
    </section>
  );
}
