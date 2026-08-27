import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../../i18n";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import ScoreViewer from "../ScoreViewer.jsx";

function renderWithI18n(ui) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("ScoreViewer real render source priority", () => {
  it("prefers backend SVG preview when present", () => {
    renderWithI18n(<ScoreViewer result={{ backend_rendered_svg_url: "/score/preview_render_artifact/r1.svg", musicxml: "<score-partwise />" }} />);

    expect(screen.getByTestId("score-source-badge").textContent).toContain("backend SVG");
    expect(screen.getByTestId("backend-score-preview")).toBeTruthy();
  });

  it("does not use ScoreDocument debug renderer as generated preview", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].events.push({
      event_id: "n1",
      type: "note",
      pitch: "C4",
      duration: "quarter",
      offset: 0,
      voice: 1,
      staff: "right_hand",
      tie: null,
      dynamic: "mf",
      articulations: [],
      selected: false
    });

    renderWithI18n(<ScoreViewer result={{ score_document: score, preview_render: { success: false, errors: ["No real backend notation renderer is available."] } }} />);

    expect(screen.getByTestId("score-source-badge").textContent).toContain("Unavailable");
    expect(screen.queryByTestId("authoritative-score-svg")).toBeNull();
    expect(screen.getByTestId("score-empty-state")).toBeTruthy();
  });
});
