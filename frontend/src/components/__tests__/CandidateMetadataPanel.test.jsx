import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import CandidateMetadataPanel from "../CandidateMetadataPanel.jsx";

describe("CandidateMetadataPanel", () => {
  it("displays selected and rejected candidate metadata", () => {
    render(
      <CandidateMetadataPanel
        metadata={{
          candidate_generation: {
            run_seed: 123,
            candidate_count: 4,
            selected_candidate_index: 2,
            selected_candidate_score: 0.87,
            selected_candidate_metrics: { melody_expectation_score: 0.9 },
            candidate_actual_diversity: { melody_diversity_score: 1, harmony_diversity_score: 0.5 },
            rejected_candidates: [{ candidate_index: 1, score: 0.4, rejection_reasons: ["low melody expectation score"] }]
          }
        }}
      />
    );

    expect(screen.getByText("Candidate generation")).toBeTruthy();
    expect(screen.getByText("melody diversity score")).toBeTruthy();
    expect(screen.getByText(/low melody expectation score/)).toBeTruthy();
  });
});
