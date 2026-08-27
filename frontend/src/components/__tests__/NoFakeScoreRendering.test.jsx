import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../../i18n";
import MidiPlayer from "../MidiPlayer.jsx";
import ScoreViewer from "../ScoreViewer.jsx";

function renderWithI18n(ui) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("V0.93 fake score rendering guard", () => {
  it("does not render plan measures as a final score", () => {
    renderWithI18n(
      <ScoreViewer
        result={{
          plan: { measures: [{ index: 1, section: "PLAN_ONLY", notes: ["1", "7"] }] }
        }}
      />
    );

    expect(screen.getByTestId("score-source-badge").textContent).toContain("Unavailable");
    expect(screen.getByTestId("score-empty-state").textContent).toContain("No authoritative score source available");
    expect(screen.queryByTestId("authoritative-score-svg")).toBeNull();
    expect(screen.queryByText("PLAN_ONLY")).toBeNull();
  });

  it("does not play plan measures as final playback", () => {
    renderWithI18n(<MidiPlayer result={{ plan: { measures: [{ index: 1, notes: ["1"] }] } }} />);

    expect(screen.getByTestId("playback-source-badge").textContent).toContain("Unavailable");
    expect(screen.getByRole("button").disabled).toBe(true);
    expect(screen.getByText("No authoritative playback source available.")).toBeTruthy();
  });
});
