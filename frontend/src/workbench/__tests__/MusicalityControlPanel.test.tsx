import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MusicalityControlPanel, { DEFAULT_MUSICALITY_CONTROLS } from "../MusicalityControlPanel";

describe("MusicalityControlPanel", () => {
  it("updates controls and runs musicality tools", () => {
    const onChange = vi.fn();
    const onApplyTool = vi.fn();
    render(<MusicalityControlPanel controls={DEFAULT_MUSICALITY_CONTROLS} onApplyTool={onApplyTool} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Rhythmic density"), { target: { value: "high" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ rhythmic_density: "high" }));
    fireEvent.click(screen.getByText("Add left-hand accompaniment"));
    expect(onApplyTool).toHaveBeenCalledWith("Add left-hand accompaniment");
  });
});
