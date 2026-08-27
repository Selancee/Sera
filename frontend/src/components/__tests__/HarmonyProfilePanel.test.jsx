import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HarmonyProfilePanel from "../HarmonyProfilePanel.jsx";
import TrackPlanPanel from "../TrackPlanPanel.jsx";

describe("HarmonyProfilePanel", () => {
  it("displays harmony profile and voice-leading report", () => {
    render(
      <HarmonyProfilePanel
        metadata={{
          harmony_profile: { style: "jazz", voicing_style: "rootless_extended", vocabulary: ["ii7", "V7", "Imaj9"] },
          voice_leading_report: { style_harmony_match_score: 0.91, parallel_fifths_count: 0 },
          voicing_source: "voicing_engine",
          actual_harmony_style_report: {
            style: "jazz",
            style_harmony_match_score: 0.95,
            contains_sevenths: true,
            contains_extensions: true,
            plain_triad_only: false,
            warnings: []
          }
        }}
      />
    );

    expect(screen.getByText("Harmony profile")).toBeTruthy();
    expect(screen.getByText("rootless_extended")).toBeTruthy();
    expect(screen.getByText("voicing_engine")).toBeTruthy();
  });

  it("displays optional track plan roles", () => {
    render(
      <TrackPlanPanel
        metadata={{
          track_plan: [{ track_id: "lead", role: "lead_melody", instrument: "piano", staff: "right_hand", voice: 1 }],
          role_coverage_report: { lead_melody: true, harmony: true, bass: false }
        }}
      />
    );

    expect(screen.getByText("Track plan")).toBeTruthy();
    expect(screen.getByText(/lead_melody/)).toBeTruthy();
  });
});
