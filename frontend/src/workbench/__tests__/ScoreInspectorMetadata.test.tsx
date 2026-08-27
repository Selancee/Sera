import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import ScoreInspector from "../ScoreInspector";

describe("ScoreInspector metadata", () => {
  it("shows title and composer fields and emits metadata operations", () => {
    const score = createEmptyScoreDocument(1);
    const onOperation = vi.fn();
    render(<ScoreInspector onOperation={onOperation} scoreDocument={score} selectedEventId="" selectedMeasureId="m1" />);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Edited Title" } });
    fireEvent.change(screen.getByLabelText("Composer"), { target: { value: "Edited Composer" } });

    expect(onOperation).toHaveBeenCalledWith(expect.objectContaining({ type: "change_title", after: { title: "Edited Title" } }));
    expect(onOperation).toHaveBeenCalledWith(expect.objectContaining({ type: "change_composer", after: { composer: "Edited Composer" } }));
  });
});
