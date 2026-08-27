import { useEffect, useState } from "react";
import { useI18n } from "../i18n/useI18n";

const SCORE_FIELDS = [
  ["prompt_adherence", "evaluation.promptAdherence"],
  ["musical_coherence", "evaluation.musicalCoherence"],
  ["notation_readability", "evaluation.notationReadability"],
  ["playability", "evaluation.playability"],
  ["editability", "evaluation.editability"]
];

const DEFAULT_RATING = {
  prompt_adherence: 4,
  musical_coherence: 4,
  notation_readability: 4,
  playability: 4,
  editability: 4,
  preference: "no_preference",
  notes: ""
};

export default function HumanEvaluationPanel({ disabled, onSubmit, result }) {
  const { t } = useI18n();
  const [rating, setRating] = useState(DEFAULT_RATING);
  const [state, setState] = useState("idle");

  useEffect(() => {
    if (result?.user_rating) {
      setRating({
        ...DEFAULT_RATING,
        ...result.user_rating
      });
      setState("saved");
    } else {
      setRating(DEFAULT_RATING);
      setState("idle");
    }
  }, [result?.run_id, result?.user_rating]);

  async function submit() {
    if (!result?.run_id || disabled) return;
    setState("saving");
    try {
      await onSubmit(rating);
      setState("saved");
    } catch {
      setState("error");
    }
  }

  function update(key, value) {
    setRating((current) => ({
      ...current,
      [key]: SCORE_FIELDS.some(([field]) => field === key) ? Number(value) : value
    }));
  }

  return (
    <section className="panel human-eval-panel">
      <div className="panel-heading">
        <h2>{t("evaluation.title")}</h2>
        <span>{state === "saved" ? t("common.saved") : state === "saving" ? t("common.saving") : result ? t("common.ready") : t("common.pending")}</span>
      </div>
      <div className="rating-grid">
        {SCORE_FIELDS.map(([key, label]) => (
          <label key={key}>
            <span>{t(label)}</span>
            <input
              disabled={!result?.run_id || disabled}
              max="5"
              min="1"
              onChange={(event) => update(key, event.target.value)}
              type="number"
              value={rating[key]}
            />
          </label>
        ))}
      </div>
      <label className="wide-field">
        <span>{t("evaluation.preference")}</span>
        <select
          disabled={!result?.run_id || disabled}
          onChange={(event) => update("preference", event.target.value)}
          value={rating.preference}
        >
          <option value="no_preference">{t("evaluation.noPreference")}</option>
          <option value="first_draft">{t("evaluation.firstDraft")}</option>
          <option value="revised">{t("evaluation.revised")}</option>
          <option value="needs_more_revision">{t("evaluation.needsMoreRevision")}</option>
        </select>
      </label>
      <label className="wide-field">
        <span>{t("evaluation.notes")}</span>
        <textarea
          disabled={!result?.run_id || disabled}
          onChange={(event) => update("notes", event.target.value)}
          rows="3"
          value={rating.notes || ""}
        />
      </label>
      <button className="secondary-action" disabled={!result?.run_id || disabled || state === "saving"} onClick={submit} type="button">
        {t("evaluation.saveRating")}
      </button>
      {state === "error" && <div className="inline-error">{t("evaluation.saveError")}</div>}
    </section>
  );
}
