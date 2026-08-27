import type { ClickToNotatePreview } from "../score/clickToNotate";
import type { ScoreCursor } from "../score/scoreCursor";
import { useI18n } from "../i18n/useI18n";
import { formatDuration, formatMusicTerm } from "../i18n/musicTerms";

export default function LocationBar({
  cursor,
  clickPreview = null,
  hoverText = "",
  selectionText = "",
  validationState = "ok"
}: {
  cursor: ScoreCursor;
  clickPreview?: ClickToNotatePreview | null;
  hoverText?: string;
  selectionText?: string;
  validationState?: "ok" | "warning" | "error" | string;
}) {
  const { t } = useI18n();
  const activeBeat = clickPreview?.beat ?? cursor.beat;
  const activePitch = clickPreview?.pitch ?? cursor.pitch;
  const activeDuration = clickPreview?.duration ?? cursor.duration;
  const activeStaff = clickPreview?.staff ?? cursor.staff;
  const activeVoice = clickPreview?.voice ?? cursor.voice;
  const clickAction = clickPreview?.action || "move_cursor";
  const insertValid = clickPreview ? (clickPreview.valid ? "valid" : "invalid") : cursor.valid ? "valid" : "invalid";
  return (
    <div className={`location-bar ${cursor.valid ? "ok" : "warning"}`} aria-label="Score location">
      <span>{t("workbench.location.measure")}: {cursor.measure_number}</span>
      <span>{t("workbench.location.beat")}: {activeBeat.toFixed(2)}</span>
      <span>{t("workbench.location.staff")}: {activeStaff === "left_hand" ? t("workbench.leftHand") : t("workbench.rightHand")}</span>
      <span>{t("workbench.location.voice")}: {activeVoice}</span>
      <span>{t("workbench.location.pitch")}: {activePitch}</span>
      <span>{t("workbench.location.duration")}: {formatDuration(activeDuration, t)}</span>
      <span>{t("workbench.location.mode")}: {formatMusicTerm(cursor.mode, t)}</span>
      <span>{t("workbench.location.snap")}: {formatMusicTerm(cursor.snap, t)}</span>
      <span>{t("workbench.location.dotted")}: {clickPreview?.dotted || cursor.duration.startsWith("dotted_") ? t("workbench.on") : t("workbench.off")}</span>
      <span>{t("workbench.location.accidental")}: {clickPreview?.accidentalMode ? formatMusicTerm(clickPreview.accidentalMode, t) : t("workbench.none")}</span>
      <span>{t("workbench.location.click")}: {formatMusicTerm(clickAction, t)}</span>
      <span>{t("workbench.location.insert")}: {insertValid === "valid" ? t("workbench.valid") : t("workbench.invalid")}</span>
      <span>{t("workbench.location.selection")}: {selectionText || t("workbench.none")}</span>
      <span>{t("workbench.location.validation")}: {clickPreview?.warning || (cursor.valid ? formatMusicTerm(validationState, t) : cursor.warning || formatMusicTerm("warning", t))}</span>
      {hoverText && <span>{t("workbench.location.hover")}: {hoverText}</span>}
    </div>
  );
}
