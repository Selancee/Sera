import { useUiText } from "../i18n/useUiText";
import type {
  StrictGenerationPreview,
  StrictScoreScope
} from "../score/scoreTypes";

const PRESETS = [
  "Transpose the selected notes up a major second while preserving rhythm.",
  "Set the selected notes to forte and staccato.",
  "Change to 5/8 while preserving all durations."
];

export default function SeraEditResearchPanel({
  instruction,
  setInstruction,
  targetScope,
  protectedScope,
  generation,
  busy,
  targetStaff,
  targetVoice,
  canUndo,
  canRedo,
  onGenerate,
  onApply,
  onReject,
  onTargetStaffChange,
  onTargetVoiceChange,
  onUndo,
  onRedo
}: {
  instruction: string;
  setInstruction: (value: string) => void;
  targetScope: StrictScoreScope;
  protectedScope: StrictScoreScope;
  generation: StrictGenerationPreview | null;
  busy: boolean;
  targetStaff: string;
  targetVoice: string;
  canUndo: boolean;
  canRedo: boolean;
  onGenerate: () => void;
  onApply: () => void;
  onReject: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onTargetStaffChange: (value: string) => void;
  onTargetVoiceChange: (value: string) => void;
}) {
  const { ui, language, systemText } = useUiText();
  const preview = generation?.preview;
  const report = preview?.validation_report;
  const patch = generation?.patch;
  const canApply = Boolean(
    patch
    && preview?.proposed_score_document
    && report
    && report.status !== "invalid"
    && report.status !== "unsupported"
    && report.errors.length === 0
  );

  return (
    <section className="workbench-panel seraedit-research-panel">
      <div className="panel-heading tight">
        <h2>{ui("SeraEdit strict editing")}</h2>
        <span>{ui("ScorePatch 1.0")}</span>
      </div>
      <p className="research-note"> {ui("Local rule demo: preview, validate, reject, and undo edits. These results are excluded from formal model experiments.")} </p>
      <label className="research-field"> {ui("Edit instruction")} <textarea
          aria-label={ui("SeraEdit instruction")}
          onChange={(event) => setInstruction(event.target.value)}
          rows={4}
          value={instruction}
        />
      </label>
      <div className="scope-card">
        <strong>{ui("Target scope")}</strong>
        <code>{ui(scopeSummary(targetScope, ui))}</code>
        <strong>{ui("Protected scope")}</strong>
        <code>{ui(scopeSummary(protectedScope, ui) || "Automatically protect everything outside the target scope")}</code>
      </div>
      <div className="strict-scope-controls">
        <label> {ui("Staff")} <select aria-label={ui("Strict editing target staff")} onChange={(event) => onTargetStaffChange(event.target.value)} value={targetStaff}>
            <option value="both">{ui("All staves")}</option>
            <option value="right_hand">{ui("Right hand / upper staff")}</option>
            <option value="left_hand">{ui("Left hand / lower staff")}</option>
          </select>
        </label>
        <label> {ui("Voice")} <select aria-label={ui("Strict editing target voice")} onChange={(event) => onTargetVoiceChange(event.target.value)} value={targetVoice}>
            <option value="all">{ui("All voices")}</option>
            <option value="1">{ui("Voice 1")}</option>
            <option value="2">{ui("Voice 2")}</option>
          </select>
        </label>
      </div>
      <div className="preset-grid">
        {PRESETS.map((preset) => (
          <button disabled={busy} key={preset} onClick={() => setInstruction(ui(preset))} type="button">
            {ui(preset)}
          </button>
        ))}
      </div>
      <div className="toolbar-row">
        <button disabled={busy || !instruction.trim()} onClick={onGenerate} type="button">
          {ui(busy ? "Validating…" : "Generate and preview")}
        </button>
        <button disabled={!canApply || busy} onClick={onApply} type="button">{ui("Apply")}</button>
        <button disabled={!generation || busy} onClick={onReject} type="button">{ui("Reject")}</button>
        <button disabled={!canUndo || busy} onClick={onUndo} type="button">{ui("Undo strict patch")}</button>
        <button disabled={!canRedo || busy} onClick={onRedo} type="button">{ui("Redo strict patch")}</button>
      </div>

      {generation && (
        <div className={`strict-result ${generation.status}`}>
          <div className="patch-summary">
            <span>{ui("generation:")} {generation.status}</span>
            <span>{ui("generator:")} {generation.generator.model}</span>
            <span className={`strict-status ${report?.status || generation.status}`}>{report?.status || generation.status}</span>
          </div>
          {generation.reason && <p className="strict-reason">{ui(systemText(generation.reason))}</p>}
          {preview && (
            <>
              <div className="diff-strip">
                <span>{ui("Changed:")} {preview.diff.changed?.length || 0}</span>
                <span>{ui("Added:")} {preview.diff.added?.length || 0}</span>
                <span>{ui("Deleted:")} {preview.diff.deleted?.length || 0}</span>
                <span>{ui("Total:")} {preview.diff.changed_element_count || 0}</span>
              </div>
              <div className="fingerprint-card">
                <span>{ui("source")}</span><code>{shortFingerprint(preview.source_fingerprint)}</code>
                <span>{ui("preview")}</span><code>{shortFingerprint(preview.post_fingerprint)}</code>
              </div>
            </>
          )}
          {report && (
            <div className="validation-card strict-validation">
              <strong>{ui("Validation report:")} {report.status}</strong>
              {!report.errors.length && !report.warnings.length && <span>{ui("All strict checks passed")}</span>}
              {[...report.errors, ...report.warnings].map((issue, index) => (
                <span key={`${issue.code}-${issue.stage}-${index}`}>
                  {issue.code} · {issue.stage}: {ui(systemText(issue.message))}
                </span>
              ))}
              <details>
                <summary>{ui("View validation layers")}</summary>
                <pre>{JSON.stringify(report.checks, null, 2)}</pre>
              </details>
            </div>
          )}
          {patch && (
            <details className="strict-json" open>
              <summary>{ui("Generated ScorePatch")}</summary>
              <pre>{JSON.stringify(patch, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function scopeSummary(scope: StrictScoreScope, ui: (text: string) => string) {
  const fields: string[] = [];
  if (scope.whole_score) fields.push("whole score");
  if (scope.measures?.length) fields.push(`M${scope.measures.join(",")}`);
  if (scope.staffs?.length) fields.push(`staff ${scope.staffs.join(",")}`);
  if (scope.voices?.length) fields.push(`voice ${scope.voices.join(",")}`);
  if (scope.event_ids?.length) fields.push(`${scope.event_ids.length} events`);
  return fields.map(ui).join(" · ");
}

function shortFingerprint(value: string) {
  if (!value) return "—";
  return `${value.slice(0, 15)}…${value.slice(-8)}`;
}
