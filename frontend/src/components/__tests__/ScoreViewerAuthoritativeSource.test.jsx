import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../../i18n";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import ScoreViewer from "../ScoreViewer.jsx";

function renderWithI18n(ui) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("ScoreViewer authoritative source", () => {
  it("uses real MusicXML OSMD preview instead of plan measures", () => {
    const score = createEmptyScoreDocument(1);
    score.measures[0].section = "REAL";
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

    renderWithI18n(
      <ScoreViewer
        onOpenWorkbench={vi.fn()}
        result={{
          run_id: "r1",
          score_document: score,
          musicxml: "<score-partwise />",
          plan: { measures: [{ index: 1, section: "PLAN_ONLY", notes: ["7"] }] }
        }}
      />
    );

    expect(screen.getByTestId("score-source-badge").textContent).toContain("OSMD");
    expect(screen.getByTestId("real-musicxml-preview")).toBeTruthy();
    expect(screen.queryByTestId("authoritative-score-svg")).toBeNull();
    expect(screen.queryByText("PLAN_ONLY")).toBeNull();
  });

  it("tries real MusicXML rendering when ScoreDocument is unavailable", () => {
    renderWithI18n(<ScoreViewer result={{ musicxml: "<score-partwise><part /></score-partwise>" }} />);

    expect(screen.getByTestId("score-source-badge").textContent).toContain("OSMD");
    expect(screen.getByTestId("real-musicxml-preview")).toBeTruthy();
  });
});
