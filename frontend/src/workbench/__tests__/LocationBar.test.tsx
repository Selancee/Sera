import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DEFAULT_SCORE_CURSOR } from "../../score/scoreCursor";
import LocationBar from "../LocationBar";

describe("LocationBar", () => {
  it("shows current cursor location", () => {
    render(<LocationBar cursor={{ ...DEFAULT_SCORE_CURSOR, measure_number: 5, beat: 2.5, duration: "eighth" }} selectionText="1 note" />);
    expect(screen.getByText("Measure: 5")).toBeTruthy();
    expect(screen.getByText("Beat: 2.50")).toBeTruthy();
    expect(screen.getByText("Selection: 1 note")).toBeTruthy();
    expect(screen.getByText("Duration: Eighth note")).toBeTruthy();
  });

  it("shows V0.91 click-to-notate feedback", () => {
    render(
      <LocationBar
        cursor={DEFAULT_SCORE_CURSOR}
        clickPreview={{
          action: "insert_note",
          valid: true,
          measureId: "m1",
          measureNumber: 1,
          beat: 2.5,
          offset: 1.5,
          staff: "left_hand",
          voice: 2,
          pitch: "Eb3",
          duration: "dotted_quarter",
          dotted: true,
          accidentalMode: "flat",
          confidence: "high",
          warning: "",
          pitchResult: { pitch: "Eb3", midi: 51, staffPosition: 0, confidence: "high", accidental: "flat" }
        }}
      />
    );

    expect(screen.getByText("Click: Insert note")).toBeTruthy();
    expect(screen.getByText("Dotted: On")).toBeTruthy();
    expect(screen.getByText("Accidental: Flat")).toBeTruthy();
    expect(screen.getByText("Insert: Valid")).toBeTruthy();
  });
});
