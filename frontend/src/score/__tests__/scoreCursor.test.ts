import { describe, expect, it } from "vitest";
import { moveScoreCursor, scoreCursorFromNoteInput, switchCursorStaff, switchCursorVoice } from "../scoreCursor";
import { DEFAULT_NOTE_INPUT_CURSOR } from "../noteInput";
import { createEmptyScoreDocument } from "../scoreTypes";

describe("scoreCursor", () => {
  it("moves by snap grid and switches staff and voice", () => {
    const score = createEmptyScoreDocument(2);
    const cursor = scoreCursorFromNoteInput(DEFAULT_NOTE_INPUT_CURSOR, "note_input", score, "eighth");
    const moved = moveScoreCursor(score, cursor, 1);
    expect(moved.offset).toBe(0.5);
    expect(switchCursorStaff(moved).staff).toBe("left_hand");
    expect(switchCursorVoice(moved).voice).toBe(2);
  });
});
