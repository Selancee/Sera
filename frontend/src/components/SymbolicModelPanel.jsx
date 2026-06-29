import { useEffect, useMemo, useState } from "react";

function formatNumber(value) {
  if (typeof value !== "number") return value || "n/a";
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}

function checkpointLabel(model) {
  return model?.available === true || model?.available === "true" ? "checkpoint ready" : "waiting for model.pt";
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
  modelRegistry,
  modelSample,
  modelStatus,
  onGenerateSample,
  onSelectModel,
  prompt,
  selectingModel,
  setPrompt
}) {
  const models = useMemo(() => {
    const registryModels = modelRegistry?.models || [];
    return registryModels.length ? registryModels : modelStatus?.known_models || [];
  }, [modelRegistry, modelStatus]);
  const activeModel = modelStatus?.active_model || modelRegistry?.active_model || "";
  const activeInfo = models.find((model) => model.name === activeModel);
  const [pendingModel, setPendingModel] = useState(activeModel);
  const metrics = modelStatus?.metrics || {};
  const rows = metricRows(metrics);
  const warnings = modelSample?.warnings || modelStatus?.warnings || [];
  const tokens = modelSample?.tokens || [];

  useEffect(() => {
    setPendingModel(activeModel);
  }, [activeModel]);

  return (
    <section className="panel model-panel">
      <div className="panel-heading">
        <h2>Symbolic Model Lab</h2>
        <span>{modelStatus?.mode || "loading"}</span>
      </div>

      <div className="model-status-strip">
        <strong>{modelStatus?.available ? "Checkpoint inference enabled" : "Recorded AutoDL sample mode"}</strong>
        <span>
          {activeModel || "No model selected"} - {modelStatus?.generator_backend || "rule_based"} backend
        </span>
      </div>

      <div className="model-selector">
        <label htmlFor="symbolic-model-select">
          <span>Runtime model</span>
          <select
            disabled={selectingModel || models.length === 0}
            id="symbolic-model-select"
            onChange={(event) => setPendingModel(event.target.value)}
            value={pendingModel}
          >
            {models.length === 0 && <option value="">No local model folders</option>}
            {models.map((model) => (
              <option key={model.name} value={model.name}>
                {model.name} - {checkpointLabel(model)}
              </option>
            ))}
          </select>
        </label>
        <button
          className="secondary-action compact-action"
          disabled={selectingModel || !pendingModel || pendingModel === activeModel}
          onClick={() => onSelectModel?.(pendingModel)}
          type="button"
        >
          {selectingModel ? "Switching..." : "Use for generation"}
        </button>
      </div>

      <div className="model-registry" aria-label="Local symbolic models">
        {models.map((model) => (
          <div className={model.name === activeModel ? "model-row active" : "model-row"} key={model.name}>
            <strong>{model.name}</strong>
            <span>{checkpointLabel(model)}</span>
          </div>
        ))}
        {models.length === 0 && <p className="muted-note">Create models/&lt;model_name&gt; to register a future checkpoint.</p>}
      </div>

      <div className="model-path-row">
        <span>Current evidence</span>
        <code>{activeInfo?.checkpoint || modelStatus?.checkpoint_path || modelStatus?.expected_model_dir || "n/a"}</code>
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
