import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import BeatGridOverlay from "../BeatGridOverlay";

describe("BeatGridOverlay", () => {
  it("renders visible beat grid lines", () => {
    render(
      <svg>
        <BeatGridOverlay scoreDocument={createEmptyScoreDocument(1)} visible />
      </svg>
    );
    expect(screen.getByLabelText("Beat grid")).toBeTruthy();
  });
});
