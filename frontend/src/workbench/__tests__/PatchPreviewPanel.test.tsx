import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PatchPreviewPanel from "../PatchPreviewPanel";

const preview = {
  patch: {
    patch_id: "p1",
    patch_type: "transform_notes",
    target_range: { start_measure: 1, end_measure: 1 },
    operations: [{ operation_id: "op1", source: "agent", type: "insert_note", target: { measure: 1 }, after: { pitch: "C4" }, description: "Insert" }],
    rationale: "rationale",
    expected_effect: "effect",
    prompt_alignment: { instruction: "", matched_aspects: [], risk_aspects: [] },
    validation_expectations: {}
  },
  patch_validation_report: { valid: true, recommendation: "accept", over_editing_risk: "low", musicxml_valid_after_patch: true },
  validation_report: { valid_musicxml: true },
  prompt_alignment_score: { overall_prompt_alignment_edit_score: 1 }
};

describe("PatchPreviewPanel", () => {
  it("accepts and partially applies valid patches", () => {
    const onAccept = vi.fn();
    const onPartialApply = vi.fn();
    render(<PatchPreviewPanel onAccept={onAccept} onPartialApply={onPartialApply} onRegenerate={vi.fn()} onReject={vi.fn()} preview={preview} />);
    fireEvent.click(screen.getByText("Accept all"));
    expect(onAccept).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Apply selected operations"));
    expect(onPartialApply).toHaveBeenCalledWith({ operation_indexes: [0] });
  });
});
