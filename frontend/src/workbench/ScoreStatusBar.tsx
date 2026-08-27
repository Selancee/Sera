import type { HitTarget } from "../score/renderers/renderTypes";
import type { RendererStatus } from "../score/renderers/renderTypes";
import type { ScoreCursor } from "../score/scoreCursor";
import type { OperationHistory, ScoreDocument } from "../score/scoreTypes";
import { useI18n } from "../i18n/useI18n";
import { formatMusicTerm } from "../i18n/musicTerms";

export default function ScoreStatusBar({
  cursor,
  hoverTarget,
  scoreDocument,
  history,
  status,
  rendererStatus,
  zoom,
  layoutMode
}: {
  cursor?: ScoreCursor;
  hoverTarget?: HitTarget | null;
  scoreDocument: ScoreDocument;
  history: OperationHistory;
  status: string;
  rendererStatus?: RendererStatus | string;
  zoom?: number;
  layoutMode?: string;
}) {
  const { t } = useI18n();
  const rendererText = typeof rendererStatus === "string" ? rendererStatus : rendererStatus ? `${formatMusicTerm(rendererStatus.activeMode, t)} ${formatMusicTerm(rendererStatus.state, t)} ${rendererStatus.renderMs}ms` : "";
  const fallbackReason = typeof rendererStatus === "object" && rendererStatus.message.includes("fallback") ? rendererStatus.message : "";
  return (
    <div className="score-status-bar">
      <span>{status}</span>
      {cursor && <span>{t("workbench.status.cursor")} M{cursor.measure_number} B{cursor.beat.toFixed(2)} {cursor.staff === "left_hand" ? t("workbench.leftHand") : t("workbench.rightHand")} V{cursor.voice}</span>}
      {hoverTarget && <span>{t("workbench.status.hover")} {formatMusicTerm(hoverTarget.type, t)} M{hoverTarget.measureNumber} {hoverTarget.confidence ? `${Math.round(hoverTarget.confidence * 100)}%` : ""}</span>}
      {rendererText && <span>{t("workbench.status.renderer")} {rendererText}</span>}
      {layoutMode && <span>{t("workbench.status.layout")} {formatMusicTerm(layoutMode, t)}</span>}
      {zoom && <span>{t("workbench.status.zoom")} {Math.round(zoom * 100)}%</span>}
      {fallbackReason && <span>{fallbackReason}</span>}
      <span>{scoreDocument.measures.length} {t("workbench.status.measures")}</span>
      <span>{history.done.length} {t("workbench.status.operations")}</span>
      <span>{scoreDocument.global.key}</span>
      <span>{scoreDocument.global.meter}</span>
      <span>{scoreDocument.global.tempo} bpm</span>
    </div>
  );
}
