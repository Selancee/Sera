import { describe, expect, it } from "vitest";
import { DEFAULT_NOTE_INPUT_CURSOR, createInsertNoteOperation } from "../noteInput";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("rhythmInput", () => {
  it("creates dotted note input operations", () => {
    const score = createEmptyScoreDocument(1);
    const op = createInsertNoteOperation(score, { ...DEFAULT_NOTE_INPUT_CURSOR, duration: "dotted_quarter", dotted: true }, "C");
    expect(op.after.duration).toBe("dotted_quarter");
  });
});
