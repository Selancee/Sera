import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n/useI18n";

export default function RealMusicXmlPreview({ musicxml }) {
  const { t } = useI18n();
  const containerRef = useRef(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function renderMusicXml() {
      if (!containerRef.current || !musicxml) {
        if (containerRef.current) {
          containerRef.current.innerHTML = "";
        }
        setStatus("idle");
        setError("");
        return;
      }
      setStatus("loading");
      setError("");
      try {
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        containerRef.current.innerHTML = "";
        const osmd = new OpenSheetMusicDisplay(containerRef.current, {
          autoResize: true,
          drawTitle: true,
          renderSingleHorizontalStaffline: false
        });
        await osmd.load(musicxml);
        osmd.zoom = 0.9;
        osmd.render();
        if (!cancelled) setStatus("ready");
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setError(err?.message || "OSMD could not render this MusicXML.");
        }
      }
    }
    renderMusicXml();
    return () => {
      cancelled = true;
    };
  }, [musicxml]);

  return (
    <div className="score-scroll real-musicxml-preview" data-testid="real-musicxml-preview">
      <div ref={containerRef} />
      {status === "loading" && <span className="render-status">{t("score.osmdRendering")}</span>}
      {status === "error" && (
        <div className="score-render-error" data-testid="osmd-render-error">
          <strong>{t("score.osmdUnavailable")}</strong>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
