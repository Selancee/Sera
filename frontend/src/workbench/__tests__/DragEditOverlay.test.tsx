import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DragEditOverlay from "../DragEditOverlay";

describe("DragEditOverlay", () => {
  it("renders drag preview details", () => {
    render(<DragEditOverlay preview={{ eventIds: ["n1"], semitones: 2, offsetDelta: 0.5, previewPitches: ["D4"], warning: "quantized" }} />);
    expect(screen.getByText("+2 st")).toBeTruthy();
    expect(screen.getByText("D4")).toBeTruthy();
  });
});
