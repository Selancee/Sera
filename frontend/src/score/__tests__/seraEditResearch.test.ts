import { describe, expect, it } from "vitest";
import {
  buildStrictScoreScopes,
  measureRangeForScope,
  recordStrictPatch,
  redoStrictPatch,
  undoStrictPatch
} from "../seraEditResearch";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("SeraEdit research scope helpers", () => {
  it("converts a selected measure range and right-hand constraint into protected scopes", () => {
    expect(buildStrictScoreScopes(
      { start_measure: 2, end_measure: 3 },
      [],
      { target_staff: "right_hand", target_voice: "1" }
    )).toEqual({
      targetScope: { measures: [2, 3], staffs: ["right_hand"], voices: [1] },
      protectedScope: { staffs: ["left_hand"] }
    });
  });

  it("keeps an explicit event selection authoritative", () => {
    const scopes = buildStrictScoreScopes(
      { start_measure: 1, end_measure: 4 },
      ["event_b", "event_a"],
      { target_staff: "both", target_voice: "all" }
    );
    expect(scopes.targetScope).toEqual({ event_ids: ["event_b", "event_a"] });
    expect(scopes.protectedScope).toEqual({});
  });

  it("derives highlight measures from event IDs", () => {
    const score = createEmptyScoreDocument(3);
    score.measures[1].events.push({
      event_id: "selected_note",
      type: "note",
      pitch: "C4",
      duration: "quarter",
      offset: 0,
      voice: 1,
      staff: "right_hand",
      tie: null,
      dynamic: "mf",
      articulations: [],
      selected: false
    });
    expect(measureRangeForScope(score, { event_ids: ["selected_note"] }, { start_measure: 1, end_measure: 1 }))
      .toEqual({ start_measure: 2, end_measure: 2 });
  });

  it("undoes and redoes only when the canonical score has not drifted", () => {
    const before = createEmptyScoreDocument(1);
    const after = { ...before, title: "After strict patch" };
    const validationReport = { status: "valid" as const, errors: [], warnings: [], checks: {}, repairable: false, suggested_repairs: [] };
    const patch = {
      schema_version: "1.0.0" as const,
      patch_id: "p1",
      source_score_id: before.score_id,
      source_fingerprint: "sha256:test",
      instruction: "test",
      target_scope: { measures: [1] },
      protected_scope: {},
      preconditions: [],
      operations: [],
      expected_effects: [],
      provenance: {}
    };
    const recorded = recordStrictPatch({ done: [], undone: [] }, { patch, beforeScore: before, afterScore: after, validationReport });
    expect(undoStrictPatch(recorded, { ...after })).toBeNull();
    const undone = undoStrictPatch(recorded, after);
    expect(undone?.scoreDocument).toBe(before);
    const redone = redoStrictPatch(undone!.history, before);
    expect(redone?.scoreDocument).toBe(after);
  });
});
