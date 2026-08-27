import { describe, expect, it } from "vitest";
import { EMPTY_OPERATION_HISTORY } from "../operationHistory";
import { applyLocalOperation, recordLocalOperation, redoLocal, undoLocal } from "../scoreOperations";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("scoreOperations metadata", () => {
  it("updates title and composer with undo redo snapshots", () => {
    const score = createEmptyScoreDocument(1);
    const titleEdit = applyLocalOperation(score, {
      source: "user",
      type: "change_title",
      target: { field: "title" },
      after: { title: "Cyberpunk Study" },
      description: "Change title"
    });
    const composerEdit = applyLocalOperation(titleEdit.scoreDocument, {
      source: "user",
      type: "change_composer",
      target: { field: "composer" },
      after: { composer: "selance" },
      description: "Change composer"
    });
    const history = recordLocalOperation(recordLocalOperation(EMPTY_OPERATION_HISTORY, titleEdit.operation), composerEdit.operation);
    const undone = undoLocal(composerEdit.scoreDocument, history);
    const redone = redoLocal(undone.scoreDocument, undone.operationHistory);

    expect(composerEdit.scoreDocument.title).toBe("Cyberpunk Study");
    expect(composerEdit.scoreDocument.composer).toBe("selance");
    expect(undone.scoreDocument.composer).toBe("Sera");
    expect(redone.scoreDocument.composer).toBe("selance");
  });
});
