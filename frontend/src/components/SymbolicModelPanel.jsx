function formatNumber(value) {
  if (typeof value !== "number") return value || "n/a";
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}

function metricRows(metrics) {
  if (!metrics || Object.keys(metrics).length === 0) return [];
  const history = metrics.history || [];
  const lastEpoch = history.length ? history[history.length - 1] : {};
  return [
    ["Mode", metrics.device || "n/a"],
    ["Rows", metrics.token_rows],
    ["Chunks", metrics.sequence_chunks],
    ["Vocab", metrics.vocab_size],
    ["Best loss", metrics.best_loss],
    ["Last val", lastEpoch.val_loss],
    ["Seconds", metrics.seconds]
  ];
}

export default function SymbolicModelPanel({
  disabled,
  modelSample,
  modelStatus,
  onGenerateSample,
  prompt,
  setPrompt
}) {
  const metrics = modelStatus?.metrics || {};
  const rows = metricRows(metrics);
  const warnings = modelSample?.warnings || modelStatus?.warnings || [];
  const tokens = modelSample?.tokens || [];

  return (
    <section className="panel model-panel">
      <div className="panel-heading">
        <h2>Symbolic Model Lab</h2>
        <span>{modelStatus?.mode || "loading"}</span>
      </div>

      <div className="model-status-strip">
        <strong>{modelStatus?.available ? "Checkpoint inference enabled" : "Recorded AutoDL sample mode"}</strong>
        <span>{modelStatus?.run_id || "No training run detected"}</span>
      </div>

      {rows.length > 0 && (
        <div className="model-metrics">
          {rows.map(([label, value]) => (
            <div className="model-metric" key={label}>
              <span>{label}</span>
              <strong>{formatNumber(value)}</strong>
            </div>
          ))}
        </div>
      )}

      <label className="wide-field" htmlFor="model-prompt">
        <span>Prompt for model test</span>
        <textarea
          id="model-prompt"
          rows="4"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
      </label>

      <button className="secondary-action" disabled={disabled || !prompt.trim()} onClick={onGenerateSample} type="button">
        Generate Model Sample
      </button>

      {warnings.length > 0 && (
        <div className="model-warnings">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}

      <div className="model-output-grid">
        <details className="json-details model-token-box" open>
          <summary>Generated tokens</summary>
          <pre>{tokens.length ? tokens.join(" ") : "Run a model sample to inspect token output."}</pre>
        </details>
        <details className="json-details model-token-box" open>
          <summary>MusicXML preview</summary>
          <pre>
            {modelSample?.musicxml_preview ||
              "Token output is not yet guaranteed to be valid MusicXML. TODO: add grammar-constrained detokenization."}
          </pre>
        </details>
      </div>
    </section>
  );
}
