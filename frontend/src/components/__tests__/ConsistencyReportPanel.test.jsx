import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../../i18n";
import ConsistencyReportPanel from "../ConsistencyReportPanel.jsx";

describe("ConsistencyReportPanel", () => {
  it("shows event counts and mismatch warnings", () => {
    render(
      <I18nProvider>
        <ConsistencyReportPanel
          report={{
            musicxml_event_count: 8,
            score_document_event_count: 8,
            midi_event_count: 6,
            mismatch_count: 1,
            warnings: ["Generated MIDI file is missing."],
            errors: []
          }}
        />
      </I18nProvider>
    );

    expect(screen.getByText("Consistency Report")).toBeTruthy();
    expect(screen.getByText("Mismatches")).toBeTruthy();
    expect(screen.getByText("Generated MIDI file is missing.")).toBeTruthy();
  });
});
