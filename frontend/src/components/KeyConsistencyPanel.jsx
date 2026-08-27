import { asArray, asObject } from "./componentDataGuards.js";

export default function KeyConsistencyPanel({ report }) {
  const data = asObject(report);
  const warnings = asArray(data.warnings);
  const errors = asArray(data.errors);
  if (!Object.keys(data).length) return null;
  return (
    <section className={`panel key-consistency-panel ${data.valid === false ? "warning" : "ok"}`}>
      <div className="panel-heading">
        <h2>Key Consistency</h2>
        <span>{data.valid === false ? "warning" : "ok"}</span>
      </div>
      <div className="metadata-editor-grid">
        <Info label="Prompt key" value={data.prompt_key} />
        <Info label="UI key" value={data.ui_key} />
        <Info label="Resolved key" value={data.resolved_key} />
        <Info label="Score key" value={data.score_document_key} />
        <Info label="Title key" value={data.title_key || "none"} />
        <Info label="MusicXML key" value={data.musicxml_key} />
      </div>
      {data.stale_key_in_title && (
        <p className="metadata-warning">
          The title appears to reference {data.title_key}, but the generated score is in {data.resolved_key || data.score_document_key}.
        </p>
      )}
      {!data.stale_key_in_title && data.title_key === null && (
        <p className="metadata-ok">Title was updated to match the final resolved key.</p>
      )}
      {[...warnings, ...errors].length > 0 && (
        <ul className="compact-list">
          {[...warnings, ...errors].map((item, index) => <li key={`${item}-${index}`}>{String(item)}</li>)}
        </ul>
      )}
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
