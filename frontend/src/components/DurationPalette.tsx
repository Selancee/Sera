import { DurationGlyphLabel } from "./NotationGlyph";
import { formatDuration } from "../i18n/musicTerms";
import { useI18n } from "../i18n/useI18n";

const DURATIONS = ["whole", "half", "quarter", "eighth", "sixteenth", "dotted_quarter", "dotted_eighth", "rest"];

export default function DurationPalette({ onSelect }: { onSelect: (duration: string) => void }) {
  const { t } = useI18n();
  return (
    <section className="workbench-tool-group">
      <h3>{t("workbench.location.duration")}</h3>
      <div className="palette-grid duration-grid">
        {DURATIONS.map((duration) => (
          <button aria-label={formatDuration(duration, t)} className="duration-button" key={duration} onClick={() => onSelect(duration)} title={formatDuration(duration, t)} type="button">
            <DurationGlyphLabel duration={duration} t={t} />
          </button>
        ))}
      </div>
    </section>
  );
}
