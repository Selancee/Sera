import type {
  StrictGenerationPreview,
  StrictScoreScope
} from "../score/scoreTypes";

const PRESETS = [
  "将选中音符升高大二度，并保持节奏不变。",
  "将选中音符设为强奏和断奏。",
  "改为5/8拍，同时保持全部时值不变。"
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
        <h2>SeraEdit 严格编辑</h2>
        <span>ScorePatch 1.0</span>
      </div>
      <p className="research-note">
        本地规则演示：结果可预览、验证、拒绝和撤销；不计入正式模型实验。
      </p>
      <label className="research-field">
        编辑指令
        <textarea
          aria-label="SeraEdit 编辑指令"
          onChange={(event) => setInstruction(event.target.value)}
          rows={4}
          value={instruction}
        />
      </label>
      <div className="scope-card">
        <strong>Target scope</strong>
        <code>{scopeSummary(targetScope)}</code>
        <strong>Protected scope</strong>
        <code>{scopeSummary(protectedScope) || "目标范围之外自动保护"}</code>
      </div>
      <div className="strict-scope-controls">
        <label>
          谱表
          <select aria-label="严格编辑目标谱表" onChange={(event) => onTargetStaffChange(event.target.value)} value={targetStaff}>
            <option value="both">全部谱表</option>
            <option value="right_hand">右手 / 上方谱表</option>
            <option value="left_hand">左手 / 下方谱表</option>
          </select>
        </label>
        <label>
          声部
          <select aria-label="严格编辑目标声部" onChange={(event) => onTargetVoiceChange(event.target.value)} value={targetVoice}>
            <option value="all">全部声部</option>
            <option value="1">声部 1</option>
            <option value="2">声部 2</option>
          </select>
        </label>
      </div>
      <div className="preset-grid">
        {PRESETS.map((preset) => (
          <button disabled={busy} key={preset} onClick={() => setInstruction(preset)} type="button">
            {preset}
          </button>
        ))}
      </div>
      <div className="toolbar-row">
        <button disabled={busy || !instruction.trim()} onClick={onGenerate} type="button">
          {busy ? "严格验证中…" : "生成并预览"}
        </button>
        <button disabled={!canApply || busy} onClick={onApply} type="button">Apply</button>
        <button disabled={!generation || busy} onClick={onReject} type="button">Reject</button>
        <button disabled={!canUndo || busy} onClick={onUndo} type="button">Undo strict patch</button>
        <button disabled={!canRedo || busy} onClick={onRedo} type="button">Redo strict patch</button>
      </div>

      {generation && (
        <div className={`strict-result ${generation.status}`}>
          <div className="patch-summary">
            <span>generation: {generation.status}</span>
            <span>generator: {generation.generator.model}</span>
            <span className={`strict-status ${report?.status || generation.status}`}>{report?.status || generation.status}</span>
          </div>
          {generation.reason && <p className="strict-reason">{generation.reason}</p>}
          {preview && (
            <>
              <div className="diff-strip">
                <span>Changed: {preview.diff.changed?.length || 0}</span>
                <span>Added: {preview.diff.added?.length || 0}</span>
                <span>Deleted: {preview.diff.deleted?.length || 0}</span>
                <span>Total: {preview.diff.changed_element_count || 0}</span>
              </div>
              <div className="fingerprint-card">
                <span>source</span><code>{shortFingerprint(preview.source_fingerprint)}</code>
                <span>preview</span><code>{shortFingerprint(preview.post_fingerprint)}</code>
              </div>
            </>
          )}
          {report && (
            <div className="validation-card strict-validation">
              <strong>Validation report: {report.status}</strong>
              {!report.errors.length && !report.warnings.length && <span>全部严格检查通过</span>}
              {[...report.errors, ...report.warnings].map((issue, index) => (
                <span key={`${issue.code}-${issue.stage}-${index}`}>
                  {issue.code} · {issue.stage}: {issue.message}
                </span>
              ))}
              <details>
                <summary>查看分层检查</summary>
                <pre>{JSON.stringify(report.checks, null, 2)}</pre>
              </details>
            </div>
          )}
          {patch && (
            <details className="strict-json" open>
              <summary>Generated ScorePatch</summary>
              <pre>{JSON.stringify(patch, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function scopeSummary(scope: StrictScoreScope) {
  const fields: string[] = [];
  if (scope.whole_score) fields.push("whole score");
  if (scope.measures?.length) fields.push(`M${scope.measures.join(",")}`);
  if (scope.staffs?.length) fields.push(`staff ${scope.staffs.join(",")}`);
  if (scope.voices?.length) fields.push(`voice ${scope.voices.join(",")}`);
  if (scope.event_ids?.length) fields.push(`${scope.event_ids.length} events`);
  return fields.join(" · ");
}

function shortFingerprint(value: string) {
  if (!value) return "—";
  return `${value.slice(0, 15)}…${value.slice(-8)}`;
}
