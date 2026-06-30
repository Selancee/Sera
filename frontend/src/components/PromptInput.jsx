const OPTIONS = {
  style: ["classical", "romantic", "jazz", "pop", "electronic", "chinese", "experimental"],
  instrument: ["piano", "synthesizer", "violin", "cello", "flute"],
  key: ["C major", "G major", "D major", "A minor", "D minor", "E minor", "F major"],
  meter: ["4/4", "3/4", "6/8"],
  length: [8, 16, 32],
  difficulty: ["beginner", "intermediate", "advanced"],
  generator_mode: ["rule_based", "model_based", "hybrid_v04", "hybrid_v05"],
  model_task_type: ["melody_fragment", "motif_variation", "cadence_generation", "rhythm_rewrite"]
};

function updateParam(params, setParams, key, value) {
  setParams({ ...params, [key]: key === "tempo" || key === "length" ? Number(value) : value });
}

export default function PromptInput({ disabled, onGenerate, params, prompt, setParams, setPrompt }) {
  return (
    <section className="panel prompt-panel">
      <div className="panel-heading">
        <h2>Prompt</h2>
        <span>{prompt.length}/2000</span>
      </div>
      <textarea
        aria-label="Prompt"
        disabled={disabled}
        maxLength={2000}
        onChange={(event) => setPrompt(event.target.value)}
        rows="7"
        value={prompt}
      />

      <div className="parameter-panel" aria-label="Quick parameters">
        {["style", "instrument", "key", "meter", "length", "difficulty", "generator_mode", "model_task_type"].map((key) => (
          <label key={key}>
            <span>{key}</span>
            <select
              value={params[key]}
              onChange={(event) => updateParam(params, setParams, key, event.target.value)}
            >
              {OPTIONS[key].map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
        ))}
        <label>
          <span>tempo</span>
          <input
            max="220"
            min="40"
            onChange={(event) => updateParam(params, setParams, "tempo", event.target.value)}
            step="1"
            type="number"
            value={params.tempo}
          />
        </label>
      </div>

      <button className="primary-action" disabled={disabled || !prompt.trim()} onClick={onGenerate} type="button">
        Generate
      </button>
    </section>
  );
}
