import { describe, expect, it } from "vitest";
import { EMPTY_OPERATION_HISTORY } from "../operationHistory";
import { applyLocalOperation, recordLocalOperation, redoLocal, undoLocal } from "../scoreOperations";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("scoreOperations", () => {
  it("inserts notes and supports undo redo snapshots", () => {
    const score = createEmptyScoreDocument(2);
    const inserted = applyLocalOperation(score, {
      source: "user",
      type: "insert_note",
      target: { measure: 1 },
      after: { pitch: "D4", duration: "quarter", offset: 0 },
      description: "Insert D4"
    });
    expect(inserted.scoreDocument.measures[0].events[0].pitch).toBe("D4");

    const history = recordLocalOperation(EMPTY_OPERATION_HISTORY, inserted.operation);
    const undone = undoLocal(inserted.scoreDocument, history);
    expect(undone.scoreDocument.measures[0].events).toHaveLength(0);

    const redone = redoLocal(undone.scoreDocument, undone.operationHistory);
    expect(redone.scoreDocument.measures[0].events[0].pitch).toBe("D4");
  });

  it("updates selected pitch", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({
      event_id: "n1",
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
    const updated = applyLocalOperation(score, {
      source: "user",
      type: "update_pitch",
      target: { measure_id: "m1", event_id: "n1" },
      after: { pitch: "E4" },
      description: "Update pitch"
    });
    expect(updated.scoreDocument.measures[0].events[0].pitch).toBe("E4");
  });
});
