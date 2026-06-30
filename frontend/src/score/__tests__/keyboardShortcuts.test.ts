import { describe, expect, it } from "vitest";
import { mapWorkbenchShortcut } from "../keyboardShortcuts";

describe("keyboardShortcuts", () => {
  it("maps note input, transport, and undo shortcuts", () => {
    expect(mapWorkbenchShortcut({ key: "A" }, "note_input")).toEqual({ type: "input_pitch", step: "A", chordTone: false });
    expect(mapWorkbenchShortcut({ key: "R" }, "note_input")).toEqual({ type: "input_rest" });
    expect(mapWorkbenchShortcut({ key: "z", ctrlKey: true }, "select")).toEqual({ type: "undo" });
    expect(mapWorkbenchShortcut({ key: " " }, "select")).toEqual({ type: "toggle_playback" });
  });
});
