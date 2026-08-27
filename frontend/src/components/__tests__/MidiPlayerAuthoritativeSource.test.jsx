import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../../i18n";
import { createEmptyScoreDocument } from "../../score/scoreTypes";
import MidiPlayer from "../MidiPlayer.jsx";

function renderWithI18n(ui) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("MidiPlayer authoritative source", () => {
  it("prefers backend MIDI export when available", () => {
    renderWithI18n(<MidiPlayer result={{ midi_url: "/export/r1/midi", plan: { measures: [{ notes: ["1"] }] } }} />);

    expect(screen.getByTestId("playback-source-badge").textContent).toContain("MIDI export");
    expect(screen.getByRole("button").textContent).toContain("Open MIDI");
  });

  it("falls back to ScoreDocument events instead of plan measures", () => {
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

    renderWithI18n(<MidiPlayer result={{ score_document: score, plan: { measures: [{ notes: ["7"] }] } }} />);

    expect(screen.getByTestId("playback-source-badge").textContent).toContain("ScoreDocument events");
    expect(screen.getByRole("button").disabled).toBe(false);
  });
});
