import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DEFAULT_NOTE_INPUT_CURSOR } from "../../score/noteInput";
import NoteInputMode from "../NoteInputMode";

describe("NoteInputMode", () => {
  it("switches mode and duration", () => {
    const onEditMode = vi.fn();
    const onDuration = vi.fn();
    render(<NoteInputMode cursor={DEFAULT_NOTE_INPUT_CURSOR} editMode="select" onCursor={vi.fn()} onDuration={onDuration} onEditMode={onEditMode} onFillRests={vi.fn()} />);
    fireEvent.click(screen.getAllByText("Note Input")[1]);
    fireEvent.click(screen.getByLabelText("Eighth note"));
    expect(onEditMode).toHaveBeenCalledWith("note_input");
    expect(onDuration).toHaveBeenCalledWith("eighth");
  });
});
