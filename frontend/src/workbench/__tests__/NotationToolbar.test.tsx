import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ScoreToolbar from "../ScoreToolbar";

const baseProps = {
  tool: "select",
  zoom: 1,
  rendererMode: "fallback",
  editMode: "select" as const,
  duration: "quarter" as const,
  dotted: false,
  accidental: "",
  staff: "right_hand",
  voice: 1,
  loop: false,
  canUndo: false,
  canRedo: false,
  onTool: vi.fn(),
  onEditMode: vi.fn(),
  onDuration: vi.fn(),
  onDotted: vi.fn(),
  onAccidental: vi.fn(),
  onStaff: vi.fn(),
  onVoice: vi.fn(),
  onRendererMode: vi.fn(),
  onUndo: vi.fn(),
  onRedo: vi.fn(),
  onNew: vi.fn(),
  onImport: vi.fn(),
  onSave: vi.fn(),
  onOpen: vi.fn(),
  onExportMusicXml: vi.fn(),
  onExportMidi: vi.fn(),
  onExportPdf: vi.fn(),
  onPlay: vi.fn(),
  onStop: vi.fn(),
  onLoop: vi.fn(),
  onZoom: vi.fn(),
  onFitWidth: vi.fn(),
  onTie: vi.fn(),
  onSlur: vi.fn()
};

describe("NotationToolbar", () => {
  it("emits notation mode and renderer actions", () => {
    render(<ScoreToolbar {...baseProps} />);
    fireEvent.click(screen.getByText("Note Input"));
    fireEvent.click(screen.getByText("Tie"));
    expect(baseProps.onEditMode).toHaveBeenCalledWith("note_input");
    expect(baseProps.onTie).toHaveBeenCalled();
  });
});
