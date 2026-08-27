import { useI18n } from "../i18n/useI18n";
import { formatFieldLabel, formatMusicTerm } from "../i18n/musicTerms";

export type MusicalityControls = {
  rhythmic_density: "low" | "medium" | "high";
  texture: string;
  accompaniment_style: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  phrase_length: number;
  cadence_strength: "light" | "clear" | "strong";
  dotted_rhythm_amount: number;
  syncopation_amount: number;
  left_hand_complexity: number;
  dynamic_contrast: number;
};

export const DEFAULT_MUSICALITY_CONTROLS: MusicalityControls = {
  rhythmic_density: "medium",
  texture: "melody_accompaniment",
  accompaniment_style: "bass_chord",
  difficulty: "intermediate",
  phrase_length: 4,
  cadence_strength: "clear",
  dotted_rhythm_amount: 0.35,
  syncopation_amount: 0.2,
  left_hand_complexity: 0.45,
  dynamic_contrast: 0.45
};

export default function MusicalityControlPanel({
  controls,
  onApplyTool,
  onChange
}: {
  controls: MusicalityControls;
  onApplyTool: (instruction: string) => void;
  onChange: (controls: MusicalityControls) => void;
}) {
  const { t } = useI18n();

  function update<K extends keyof MusicalityControls>(key: K, value: MusicalityControls[K]) {
    onChange({ ...controls, [key]: value });
  }

  return (
    <section className="workbench-panel musicality-panel">
      <h2>{formatFieldLabel("musical_controls", t)}</h2>
      <div className="constraint-grid">
        <label>
          {formatFieldLabel("rhythmic_density", t)}
          <select value={controls.rhythmic_density} onChange={(event) => update("rhythmic_density", event.target.value as MusicalityControls["rhythmic_density"])}>
            <option value="low">{formatMusicTerm("low", t)}</option>
            <option value="medium">{formatMusicTerm("medium", t)}</option>
            <option value="high">{formatMusicTerm("high", t)}</option>
          </select>
        </label>
        <label>
          {formatFieldLabel("texture", t)}
          <select value={controls.texture} onChange={(event) => update("texture", event.target.value)}>
            <option value="melody_accompaniment">{formatMusicTerm("melody_accompaniment", t)}</option>
            <option value="arpeggiated">{formatMusicTerm("arpeggiated", t)}</option>
            <option value="alberti">{formatMusicTerm("alberti", t)}</option>
            <option value="waltz">{formatMusicTerm("waltz", t)}</option>
            <option value="bass_chord">{formatMusicTerm("bass_chord", t)}</option>
          </select>
        </label>
        <label>
          {formatFieldLabel("accompaniment_style", t)}
          <select value={controls.accompaniment_style} onChange={(event) => update("accompaniment_style", event.target.value)}>
            <option value="sparse_beginner_bass">{formatMusicTerm("sparse_beginner_bass", t)}</option>
            <option value="block_chords">{formatMusicTerm("block_chords", t)}</option>
            <option value="arpeggiated_chords">{formatMusicTerm("arpeggiated_chords", t)}</option>
            <option value="alberti_bass">{formatMusicTerm("alberti_bass", t)}</option>
            <option value="bass_chord">{formatMusicTerm("bass_chord", t)}</option>
          </select>
        </label>
        <label>
          {formatFieldLabel("difficulty", t)}
          <select value={controls.difficulty} onChange={(event) => update("difficulty", event.target.value as MusicalityControls["difficulty"])}>
            <option value="beginner">{formatMusicTerm("beginner", t)}</option>
            <option value="intermediate">{formatMusicTerm("intermediate", t)}</option>
            <option value="advanced">{formatMusicTerm("advanced", t)}</option>
          </select>
        </label>
        {[
          "dotted_rhythm_amount",
          "syncopation_amount",
          "left_hand_complexity",
          "dynamic_contrast"
        ].map((key) => (
          <label key={key}>
            {formatFieldLabel(key, t)}
            <input max="1" min="0" step="0.05" type="range" value={Number(controls[key as keyof MusicalityControls])} onChange={(event) => update(key as keyof MusicalityControls, Number(event.target.value) as never)} />
          </label>
        ))}
      </div>
      <div className="agent-tool-grid">
        <button onClick={() => onApplyTool("Regenerate selected measures with richer rhythm")} type="button">{t("musicality.tool.richerRhythm")}</button>
        <button onClick={() => onApplyTool("Add left-hand accompaniment")} type="button">{t("musicality.tool.leftHand")}</button>
        <button onClick={() => onApplyTool("Add cadence")} type="button">{t("musicality.tool.cadence")}</button>
        <button onClick={() => onApplyTool("Increase rhythmic density")} type="button">{t("musicality.tool.rhythmicDensity")}</button>
        <button onClick={() => onApplyTool("Make more flowing")} type="button">{t("musicality.tool.flowingTexture")}</button>
      </div>
    </section>
  );
}
