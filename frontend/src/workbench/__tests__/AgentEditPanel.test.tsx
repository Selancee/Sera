import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AgentEditPanel from "../AgentEditPanel";

describe("AgentEditPanel", () => {
  it("passes constraints to agent edit and routes explanation separately", () => {
    const onAgentEdit = vi.fn();
    const onExplain = vi.fn();
    render(
      <AgentEditPanel
        constraints={{ preserve_harmony: true, patch_size_limit: "small" }}
        disabled={false}
        instruction="Make more lyrical"
        onAgentEdit={onAgentEdit}
        onConstraintsChange={vi.fn()}
        onExplain={onExplain}
        selectedRange={{ start_measure: 1, end_measure: 2 }}
        setInstruction={vi.fn()}
      />
    );
    fireEvent.click(screen.getByText("Preview Agent Patch"));
    expect(onAgentEdit).toHaveBeenCalledWith("Make more lyrical", expect.objectContaining({ preserve_harmony: true }));
    fireEvent.click(screen.getByText("Explain"));
    expect(onExplain).toHaveBeenCalled();
  });
});
