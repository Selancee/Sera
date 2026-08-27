import { asObject } from "./componentDataGuards.js";

export default function ScoreMetadataPanel({ onMetadataChange, result }) {
  const scoreDocument = asObject(result?.score_document);
  const report = asObject(result?.key_consistency_report || result?.generation_metadata?.key_consistency_report);
  const title = String(scoreDocument.title || result?.intent?.title || "");
  const composer = String(scoreDocument.composer || "Sera");
  return (
    <section className="panel score-metadata-panel">
      <div className="panel-heading">
        <h2>Score Metadata</h2>
        <span>{report.valid === false ? "review" : result ? "ready" : "pending"}</span>
      </div>
      <div className="metadata-editor-grid">
        <label>
          Title
          <input
            disabled={!result}
            value={title}
            onChange={(event) => onMetadataChange?.("title", event.target.value)}
          />
        </label>
        <label>
          Composer
          <input
            disabled={!result}
            value={composer}
            onChange={(event) => onMetadataChange?.("composer", event.target.value)}
          />
        </label>
        <Info label="Score key" value={scoreDocument.global?.key || report.score_document_key} />
        <Info label="Prompt key" value={report.prompt_key} />
        <Info label="UI key" value={report.ui_key} />
        <Info label="Resolved key" value={report.resolved_key} />
      </div>
    </section>
  );
}

function Info({ label, value }) {
  return (
    <div className="metadata-info-item">
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}
