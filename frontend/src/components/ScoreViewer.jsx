import { resolveBackendBaseUrl } from "../desktop/desktopRuntime";
import { resolveScoreRenderSource } from "../score/fakeScoreGuard";
import { downloadTextFile } from "../score/musicxmlAdapter";
import { useI18n } from "../i18n/useI18n";
import { formatMusicTerm } from "../i18n/musicTerms";
import { asArray, displayValue } from "./componentDataGuards.js";
import RealMusicXmlPreview from "./RealMusicXmlPreview.jsx";
import ScoreSourceBadge from "./ScoreSourceBadge.jsx";

export default function ScoreViewer({ onOpenWorkbench, onPlayMidi, rendererStatus, result }) {
  const { t } = useI18n();
  const sourceResolution = resolveScoreRenderSource(result);
  const { scoreDocument, musicxml, source } = sourceResolution;
  const musicxmlPreview = musicxml ? musicxml.slice(0, 3000) : "";
  const generation = result?.generation || result?.generation_metadata || {};
  const symbolicModel = result?.metadata?.symbolic_model || {};
  const instrumentation = asArray(result?.intent?.instrumentation ?? result?.intent?.instruments);
  const downloadName = `${result?.run_id || "sera-generated"}.musicxml`;
  const midiUrl = result?.midi_url || result?.exports?.midi || "";

  return (
    <section className="panel score-panel">
      <div className="panel-heading">
        <h2>{t("score.renderedScore")}</h2>
        <span>{instrumentation.length ? instrumentation.map((item) => formatMusicTerm(displayValue(item), t)).join(", ") : "MusicXML"}</span>
      </div>
      <div className="score-source-row">
        <ScoreSourceBadge source={source} />
        {sourceResolution.warning && <span className="source-warning">{sourceResolution.warning}</span>}
      </div>
      {source === "backend_svg" && <BackendPreview url={sourceResolution.backendUrl} title="SVG score preview" />}
      {source === "backend_png" && <BackendPreview url={sourceResolution.backendUrl} title="PNG score preview" />}
      {source === "musicxml_osmd" && musicxml && <RealMusicXmlPreview musicxml={musicxml} />}
      {source === "musicxml_text" && musicxml && (
        <pre className="musicxml-render-fallback" data-testid="musicxml-render-fallback">
          {musicxmlPreview}
        </pre>
      )}
      {source === "unavailable" && (
        <div className="empty-state score-render-error" data-testid="score-empty-state">
          <strong>{sourceResolution.error ? t("score.noAuthoritativeScoreSource") : t("score.noAuthoritativeScore")}</strong>
        </div>
      )}
      <div className="score-action-row">
        <button disabled={!scoreDocument} onClick={onOpenWorkbench} type="button">
          {t("score.openWorkbench")}
        </button>
        <button disabled={!musicxml} onClick={() => downloadTextFile(downloadName, musicxml)} type="button">
          {t("score.downloadMusicxml")}
        </button>
        <button disabled={!midiUrl} onClick={onPlayMidi} type="button">
          {t("score.playGeneratedMidi")}
        </button>
      </div>
      <div className="musicxml-strip">
        <span>MusicXML</span>
        <code>{result?.artifacts?.musicxml_path || result?.exports?.musicxml || "pending"}</code>
      </div>
      {result && (
        <div className="musicxml-strip generation-strip">
          <span>{formatMusicTerm(generation.generator_mode || result?.metadata?.generator_mode || "generator", t)}</span>
          <code>
            {symbolicModel.loaded
              ? `${symbolicModel.name || "symbolic model"} checkpoint`
              : formatMusicTerm("rule_based", t)}
          </code>
        </div>
      )}
      <details className="json-details musicxml-preview">
        <summary>{t("score.musicxmlTextPreview")}</summary>
        <pre>{musicxmlPreview || t("score.musicxmlEmpty")}</pre>
      </details>
      <details className="json-details render-source-debug">
        <summary>{t("score.renderSourceDebug")}</summary>
        <pre>
          {JSON.stringify(
            {
              source,
              score_id: scoreDocument?.score_id || "",
              run_id: result?.run_id || "",
              backend_url: sourceResolution.backendUrl,
              preview_render: result?.preview_render || generation.preview_render || null,
              renderer_status: rendererStatus || null
            },
            null,
            2
          )}
        </pre>
      </details>
    </section>
  );
}

function BackendPreview({ title, url }) {
  const absolute = absoluteUrl(url);
  return (
    <div className="score-scroll backend-preview" data-testid="backend-score-preview">
      <img alt={title} className="backend-preview-image" src={absolute} />
    </div>
  );
}

function absoluteUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return `${resolveBackendBaseUrl()}${url.startsWith("/") ? "" : "/"}${url}`;
}
