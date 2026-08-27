import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DEFAULT_SCORE_CURSOR } from "../../score/scoreCursor";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import ScoreCursorOverlay from "../ScoreCursorOverlay";

describe("ScoreCursorOverlay", () => {
  it("renders a persistent cursor marker", () => {
    render(
      <svg>
        <ScoreCursorOverlay cursor={DEFAULT_SCORE_CURSOR} scoreDocument={createEmptyScoreDocument(1)} />
      </svg>
    );
    expect(screen.getByLabelText("Score cursor")).toBeTruthy();
  });
});
