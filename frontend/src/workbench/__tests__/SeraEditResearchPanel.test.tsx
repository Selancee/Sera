import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SeraEditResearchPanel from "../SeraEditResearchPanel";

describe("SeraEditResearchPanel", () => {
  it("shows strict scope and starts generation", () => {
    const onGenerate = vi.fn();
    const setInstruction = vi.fn();
    render(
      <SeraEditResearchPanel
        busy={false}
        canRedo={false}
        canUndo={false}
        generation={null}
        instruction="升高大二度"
        onApply={vi.fn()}
        onGenerate={onGenerate}
        onRedo={vi.fn()}
        onReject={vi.fn()}
        onTargetStaffChange={vi.fn()}
        onTargetVoiceChange={vi.fn()}
        onUndo={vi.fn()}
        protectedScope={{ staffs: ["left_hand"] }}
        setInstruction={setInstruction}
        targetScope={{ measures: [1], staffs: ["right_hand"] }}
        targetStaff="right_hand"
        targetVoice="1"
      />
    );

    expect(screen.getByText("M1 · staff right_hand")).toBeTruthy();
    fireEvent.click(screen.getByText("生成并预览"));
    expect(onGenerate).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByText("将选中音符设为强奏和断奏。"));
    expect(setInstruction).toHaveBeenCalledWith("将选中音符设为强奏和断奏。");
  });

  it("renders validation and enables apply for a warning-only proposal", () => {
    const onApply = vi.fn();
    render(
      <SeraEditResearchPanel
        busy={false}
        canRedo={false}
        canUndo={true}
        generation={{
          status: "generated",
          reason: null,
          matched_intents: ["transpose"],
          generator: { provider: "local_rule", model: "seraedit_rule_v1", formal_experiment_eligible: false },
          patch: {
            schema_version: "1.0.0",
            patch_id: "p1",
            source_score_id: "s1",
            source_fingerprint: "sha256:source",
            instruction: "transpose",
            target_scope: { measures: [1] },
            protected_scope: {},
            preconditions: [],
            operations: [],
            expected_effects: [],
            provenance: {}
          },
          preview: {
            committed: false,
            score_document: {} as never,
            proposed_score_document: {} as never,
            validation_report: { status: "warning", errors: [], warnings: [], checks: {}, repairable: false, suggested_repairs: [] },
            diff: { added: [], deleted: [], changed: [], global_changes: {}, changed_element_count: 0 },
            audit: [],
            source_fingerprint: "sha256:source",
            post_fingerprint: "sha256:after",
            musicxml: null,
            rollback_reason: null
          }
        }}
        instruction="transpose"
        onApply={onApply}
        onGenerate={vi.fn()}
        onRedo={vi.fn()}
        onReject={vi.fn()}
        onTargetStaffChange={vi.fn()}
        onTargetVoiceChange={vi.fn()}
        onUndo={vi.fn()}
        protectedScope={{}}
        setInstruction={vi.fn()}
        targetScope={{ measures: [1] }}
        targetStaff="both"
        targetVoice="all"
      />
    );

    expect(screen.getByText("全部严格检查通过")).toBeTruthy();
    fireEvent.click(screen.getByText("Apply"));
    expect(onApply).toHaveBeenCalledOnce();
  });
});
