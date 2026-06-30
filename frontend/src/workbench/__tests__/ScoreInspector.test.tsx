import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import ScoreInspector from "../ScoreInspector";

describe("ScoreInspector", () => {
  it("emits operations from global controls", () => {
    const score = createEmptyScoreDocument(1);
    const onOperation = vi.fn();
    render(<ScoreInspector onOperation={onOperation} scoreDocument={score} selectedEventId="" selectedMeasureId="m1" />);
    fireEvent.change(screen.getByLabelText("Tempo"), { target: { value: "120" } });
    expect(onOperation).toHaveBeenCalledWith(expect.objectContaining({ type: "change_tempo" }));
  });
});
