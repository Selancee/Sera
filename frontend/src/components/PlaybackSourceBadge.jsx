import { useI18n } from "../i18n/useI18n";

export default function PlaybackSourceBadge({ source }) {
  const { t } = useI18n();
  const label = source === "midi_export" ? "MIDI export" : source === "backend_note_events" ? "Backend note events" : source === "score_document" ? "ScoreDocument events" : "Unavailable";
  return (
    <span className={`source-badge source-${source || "unavailable"}`} data-testid="playback-source-badge">
      {t("score.playbackSource")}: {label}
    </span>
  );
}
