import { useMemo, useState } from "react";
import { computeScoreDiff } from "../score/scoreDiff";
import { patchCanAccept } from "../score/scorePatches";
import type { ScorePatch } from "../score/scoreTypes";
import DiffLegend from "./DiffLegend";
import PartialApplyPanel from "./PartialApplyPanel";

export default function PatchPreviewPanel({
  preview,
  onAccept,
  onReject,
  onRegenerate,
  onPartialApply
}: {
  preview: any;
  onAccept: () => void;
  onReject: () => void;
  onRegenerate: () => void;
  onPartialApply: (options: { operation_indexes?: number[]; apply_filter?: string }) => void;
}) {
  const [selectedIndexes, setSelectedIndexes] = useState<number[]>([]);
  const patch = preview?.patch as ScorePatch | undefined;
  const diff = useMemo(() => {
    if (!preview?.before_score_document || !preview?.after_score_document || !patch) return preview?.diff;
    return computeScoreDiff(preview.before_score_document, preview.after_score_document, patch);
  }, [preview, patch]);

  if (!patch) {
    return (
      <section className="workbench-panel patch-panel">
        <h2>Patch Preview</h2>
        <span>No patch pending.</span>
      </section>
    );
  }

  const report = preview.patch_validation_report || {};
  const canAccept = patchCanAccept(preview);
  function toggle(index: number) {
    setSelectedIndexes((current) => current.includes(index) ? current.filter((item) => item !== index) : [...current, index]);
  }

  return (
    <section className="workbench-panel patch-panel">
      <div className="panel-heading tight">
        <h2>Patch Preview</h2>
        <span>{patch.patch_type}</span>
      </div>
      <div className="patch-summary">
        <span>Measures {patch.target_range.start_measure}-{patch.target_range.end_measure}</span>
        <span>{patch.operations.length} operations</span>
        <span className={`recommendation ${report.recommendation || "review"}`}>{report.recommendation || "review"}</span>
      </div>
      <DiffLegend />
      <p>{patch.rationale}</p>
      <p>{patch.expected_effect}</p>
      <div className="diff-strip">
        <span>Added: {diff?.added ?? 0}</span>
        <span>Removed: {diff?.removed ?? 0}</span>
        <span>Changed: {diff?.changed ?? 0}</span>
        <span>Pitch: {diff?.pitch_changed ?? 0}</span>
        <span>Duration: {diff?.duration_changed ?? 0}</span>
        <span>Harmony: {diff?.harmony_changed ?? 0}</span>
      </div>
      <div className="validation-card">
        <strong>Patch validation</strong>
        <span>risk: {report.over_editing_risk || "unknown"}</span>
        <span>{report.musicxml_valid_after_patch ? "MusicXML valid after patch" : "MusicXML needs review"}</span>
        {!!report.errors?.length && <small>{report.errors.join("; ")}</small>}
        {!!report.warnings?.length && <small>{report.warnings.join("; ")}</small>}
      </div>
      <div className="alignment-grid">
        {Object.entries(preview.prompt_alignment_score || {}).map(([key, value]) => (
          <div className="intent-item" key={key}>
            <span>{key.replaceAll("_", " ")}</span>
            <strong>{String(value)}</strong>
          </div>
        ))}
      </div>
      <PartialApplyPanel
        onApplyFilter={(apply_filter) => onPartialApply({ apply_filter })}
        onApplySelected={() => onPartialApply({ operation_indexes: selectedIndexes })}
        onToggle={toggle}
        operations={patch.operations}
        selectedIndexes={selectedIndexes}
      />
      <div className="toolbar-row">
        <button disabled={!canAccept} onClick={onAccept} type="button">Accept all</button>
        <button onClick={onReject} type="button">Reject</button>
        <button onClick={onRegenerate} type="button">Regenerate patch</button>
      </div>
    </section>
  );
}
