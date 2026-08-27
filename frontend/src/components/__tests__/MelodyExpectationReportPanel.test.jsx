import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MelodyExpectationReportPanel from "../MelodyExpectationReportPanel.jsx";

describe("MelodyExpectationReportPanel", () => {
  it("displays expectation metrics", () => {
    render(
      <MelodyExpectationReportPanel
        report={{
          melody_expectation_score: 0.82,
          leap_reversal_rate: 1,
          mean_regression_score: 0.8,
          gap_fill_score: 0.75,
          closure_score: 0.9,
          unresolved_tritone_count: 0,
          unresolved_dissonance_count: 1
        }}
        metadata={{
          melody_generation_source: "phrase_melody_engine",
          melody_candidate_count: 4,
          selected_melody_candidate_index: 1,
          phrase_melody: {
            phrase_level_scores: {
              phrase_contour_score: 0.7,
              motif_development_score: 0.8,
              target_tone_hit_score: 0.75,
              mechanical_template_penalty: 0.1
            }
          }
        }}
      />
    );

    expect(screen.getByText("Melody expectation")).toBeTruthy();
    expect(screen.getByText("phrase_melody_engine")).toBeTruthy();
    expect(screen.getByText("phrase contour")).toBeTruthy();
    expect(screen.getByText("gap fill")).toBeTruthy();
  });
});
