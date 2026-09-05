import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createEmptyScoreDocument, type ScoreDocument, type ScoreEvent, type StrictGenerationPreview } from "../../score/scoreTypes";
import StrictScoreComparison, { compareDocuments } from "../StrictScoreComparison";

function note(eventId: string, staff: string, pitch: string): ScoreEvent {
  return {
    event_id: eventId,
    type: "note",
    pitch,
    duration: "quarter",
    offset: 0,
    voice: 1,
    staff,
    tie: null,
    slur: null,
    dynamic: "mf",
    articulations: [],
    selected: false,
    part_id: "piano"
  };
}

function documents(): { before: ScoreDocument; after: ScoreDocument } {
  const before = createEmptyScoreDocument(1);
  before.measures[0].events = [note("right-1", "right_hand", "C4"), note("left-1", "left_hand", "C3")];
  const after = structuredClone(before);
  after.measures[0].events[0].pitch = "D4";
  return { before, after };
}

describe("StrictScoreComparison", () => {
  it("classifies target and protected changes using conjunctive scopes", () => {
    const { before, after } = documents();
    after.measures[0].events[1].duration = "half";
    const comparison = compareDocuments(
      before,
      after,
      { measures: [1], staffs: ["right_hand"] },
      { staffs: ["left_hand"] }
    );
    expect(comparison.rows).toHaveLength(2);
    expect(comparison.rows.find((row) => row.eventId === "right-1")?.scope).toBe("target");
    expect(comparison.rows.find((row) => row.eventId === "left-1")?.scope).toBe("protected");
    expect(comparison.protectedChanges).toBe(1);
  });

  it("renders an unapplied before/after proposal in the central workflow", () => {
    const { before, after } = documents();
    const generation: StrictGenerationPreview = {
      status: "generated",
      reason: null,
      matched_intents: ["transpose"],
      generator: { provider: "local_rule", model: "test", formal_experiment_eligible: false },
      patch: {
        schema_version: "1.0.0",
        patch_id: "patch-1",
        source_score_id: before.score_id,
        source_fingerprint: `sha256:${"a".repeat(64)}`,
        instruction: "transpose",
        target_scope: { measures: [1], staffs: ["right_hand"] },
        protected_scope: { staffs: ["left_hand"] },
        preconditions: [],
        operations: [],
        expected_effects: [],
        provenance: {}
      },
      preview: {
        committed: false,
        score_document: before,
        proposed_score_document: after,
        validation_report: { status: "valid", errors: [], warnings: [], checks: {}, repairable: false, suggested_repairs: [] },
        diff: { added: [], deleted: [], changed: [], global_changes: {}, changed_element_count: 1 },
        audit: [],
        source_fingerprint: `sha256:${"a".repeat(64)}`,
        post_fingerprint: `sha256:${"b".repeat(64)}`,
        musicxml: null,
        rollback_reason: null
      }
    };
    render(<StrictScoreComparison generation={generation} />);
    expect(screen.getByText("Current score and ScorePatch proposal")).toBeTruthy();
    expect(screen.getByText("C4")).toBeTruthy();
    expect(screen.getByText("D4")).toBeTruthy();
    expect(screen.getByText("Unexpected protected changes 0")).toBeTruthy();
  });
});
