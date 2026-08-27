import { useI18n } from "../i18n/useI18n";

export default function ScoreSourceBadge({ source }) {
  const { t } = useI18n();
  const labels = {
    backend_svg: "Real Notation: backend SVG",
    backend_png: "Real Notation: backend PNG",
    score_document: "Debug Fallback Only",
    musicxml_osmd: "Real Notation: OSMD",
    musicxml_text: "MusicXML Text Preview",
    unavailable: "Unavailable"
  };
  const label = labels[source] || labels.unavailable;
  return (
    <span className={`source-badge source-${source || "unavailable"}`} data-testid="score-source-badge">
      {t("score.source")}: {label}
    </span>
  );
}
