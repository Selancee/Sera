import { describe, expect, it } from "vitest";
import { staffAndPitchFromPoint } from "../staffLanes";

describe("staffLanes", () => {
  it("maps vertical position to right and left hand lanes", () => {
    expect(staffAndPitchFromPoint({ x: 80, y: 90 }).staff).toBe("right_hand");
    expect(staffAndPitchFromPoint({ x: 80, y: 170 }).staff).toBe("left_hand");
  });
});
