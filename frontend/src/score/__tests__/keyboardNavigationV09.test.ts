import { describe, expect, it } from "vitest";
import { mapWorkbenchShortcut } from "../keyboardShortcuts";

describe("keyboardNavigationV09", () => {
  it("maps MuseScore-like cursor navigation shortcuts", () => {
    expect(mapWorkbenchShortcut({ key: "ArrowRight" }, "select")).toEqual({ type: "cursor_step", steps: 1 });
    expect(mapWorkbenchShortcut({ key: "ArrowLeft", ctrlKey: true }, "select")).toEqual({ type: "cursor_measure", delta: -1 });
    expect(mapWorkbenchShortcut({ key: "Tab", shiftKey: true }, "select")).toEqual({ type: "switch_staff", reverse: true });
    expect(mapWorkbenchShortcut({ key: "V" }, "select")).toEqual({ type: "switch_voice" });
    expect(mapWorkbenchShortcut({ key: "N" }, "select")).toEqual({ type: "toggle_note_input" });
  });
});
