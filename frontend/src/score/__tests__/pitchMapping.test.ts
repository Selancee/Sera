import { describe, expect, it } from "vitest";
import { defaultStaffLayout, mapYToPitch } from "../pitchMapping";

describe("pitchMapping", () => {
  it("maps treble staff y positions to octave-aware pitches", () => {
    const result = mapYToPitch({
      y: 92,
      staffId: "right_hand",
      clef: "treble",
      staffLayout: defaultStaffLayout("right_hand", "treble")
    });

    expect(result.pitch).toMatch(/^[A-G][#b]?\d$/);
    expect(result.midi).toBeGreaterThan(55);
    expect(result.confidence).toBe("high");
  });

  it("applies accidental mode", () => {
    const result = mapYToPitch({
      y: 160,
      staffId: "left_hand",
      clef: "bass",
      staffLayout: defaultStaffLayout("left_hand", "bass"),
      accidentalMode: "flat"
    });

    expect(result.pitch).toContain("b");
    expect(result.accidental).toBe("flat");
  });
});
