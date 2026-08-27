import { useI18n } from "../i18n/useI18n";
import { formatFieldLabel, formatMusicTerm } from "../i18n/musicTerms";

const OPTIONS = {
  style: ["classical", "romantic", "jazz", "pop", "electronic", "chinese", "experimental"],
  instrument: ["piano", "synthesizer", "violin", "cello", "flute"],
  key: ["C major", "G major", "D major", "A minor", "D minor", "E minor", "F major"],
  meter: ["4/4", "3/4", "6/8"],
  length: [8, 16, 32],
  difficulty: ["beginner", "intermediate", "advanced"],
  rhythmic_density: ["low", "medium", "high"],
  texture: ["melody_accompaniment", "arpeggiated", "chordal", "waltz", "alberti", "bass_chord"],
  accompaniment_style: ["sparse_beginner_bass", "block_chords", "arpeggiated_chords", "alberti_bass", "bass_chord", "waltz_bass"],
  cadence_strength: ["light", "clear", "strong"],
  generator_mode: ["rule_based", "model_based", "hybrid_v04", "hybrid_v05"],
  model_task_type: ["melody_fragment", "motif_variation", "cadence_generation", "rhythm_rewrite"]
};

function updateParam(params, setParams, key, value, onParamChange) {
  const normalized = key === "tempo" || key === "length" ? Number(value) : value;
  if (onParamChange) {
    onParamChange(key, normalized);
    return;
  }
  setParams({ ...params, [key]: normalized });
}

const PROMPT_PLACEHOLDER = "Describe the music you want... e.g. cyberpunk piano, mechanical pulse, syncopation, repeating bass, 8 measures";

export default function PromptInput({ controlOnly = false, disabled, onGenerate, onParamChange, params, prompt, setParams, setPrompt }) {
  const { t } = useI18n();
  return (
    <section className="panel prompt-panel">
      <div className="panel-heading">
        <h2>{t("prompt.title")}</h2>
        <span>{prompt.length}/2000</span>
      </div>
      <textarea
        aria-label={t("prompt.aria")}
        disabled={disabled}
        maxLength={2000}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder={PROMPT_PLACEHOLDER}
        rows="7"
        value={prompt}
      />
      {controlOnly && <div className="control-only-indicator">Generating from controls only</div>}

      <div className="parameter-panel" aria-label={t("prompt.quickParameters")}>
        {["style", "instrument", "key", "meter", "length", "difficulty", "rhythmic_density", "texture", "accompaniment_style", "cadence_strength", "generator_mode", "model_task_type"].map((key) => (
          <label key={key}>
            <span>{formatFieldLabel(key, t)}</span>
            <select
              value={params[key]}
              onChange={(event) => updateParam(params, setParams, key, event.target.value, onParamChange)}
            >
              {OPTIONS[key].map((option) => (
                <option key={option} value={option}>{formatMusicTerm(option, t)}</option>
              ))}
            </select>
          </label>
        ))}
        <label>
          <span>{t("prompt.tempo")}</span>
          <input
            max="220"
            min="40"
            onChange={(event) => updateParam(params, setParams, "tempo", event.target.value, onParamChange)}
            step="1"
            type="number"
            value={params.tempo}
          />
        </label>
      </div>

      <button className="primary-action" disabled={disabled} onClick={onGenerate} type="button">
        {t("prompt.generate")}
      </button>
    </section>
  );
}
