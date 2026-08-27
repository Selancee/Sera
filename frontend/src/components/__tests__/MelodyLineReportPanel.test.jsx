import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MelodyLineReportPanel from "../MelodyLineReportPanel.jsx";

describe("MelodyLineReportPanel", () => {
  it("distinguishes primary melody from playback events", () => {
    render(
      <MelodyLineReportPanel
        crossMeasureReport={{ valid: true, cross_measure_tritone_rate: 0, cross_measure_large_leap_count: 0, unresolved_cross_measure_leap_count: 0 }}
        report={{
          primary_melody: { staff: "right_hand", voice: 1, events: [{ event_id: "n1" }] },
          excluded_lines: [{ staff: "left_hand", voice: 1, reason: "accompaniment" }]
        }}
      />
    );

    expect(screen.getByText(/not from mixed playback events/i)).toBeTruthy();
    expect(screen.getByText(/left_hand voice 1: accompaniment/i)).toBeTruthy();
  });
});
