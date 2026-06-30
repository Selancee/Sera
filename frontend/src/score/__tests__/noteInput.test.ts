import { describe, expect, it } from "vitest";
import { createInsertNoteOperation, createInsertRestOperation, DEFAULT_NOTE_INPUT_CURSOR, advanceCursor, canInsertAtCursor, durationFromKey } from "../noteInput";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("noteInput", () => {
  it("maps duration keys and creates note/rest operations", () => {
    const score = createEmptyScoreDocument(1);
    expect(durationFromKey("4")).toBe("quarter");
    const note = createInsertNoteOperation(score, DEFAULT_NOTE_INPUT_CURSOR, "C");
    const rest = createInsertRestOperation(score, DEFAULT_NOTE_INPUT_CURSOR);
    expect(note.type).toBe("insert_note");
    expect(note.after.pitch).toBe("C4");
    expect(rest.type).toBe("insert_rest");
  });

  it("advances cursor and blocks measure overflow", () => {
    const score = createEmptyScoreDocument(1);
    const cursor = { ...DEFAULT_NOTE_INPUT_CURSOR, offset: 3.5, duration: "half" as const };
    expect(canInsertAtCursor(score, cursor).ok).toBe(false);
    const advanced = advanceCursor(score, { ...DEFAULT_NOTE_INPUT_CURSOR, duration: "quarter" });
    expect(advanced.offset).toBe(1);
  });
});
