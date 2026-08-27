import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ScoreMetadataPanel from "../ScoreMetadataPanel.jsx";

describe("ScoreMetadataPanel", () => {
  it("displays keys and emits title composer edits", () => {
    const onMetadataChange = vi.fn();
    render(
      <ScoreMetadataPanel
        onMetadataChange={onMetadataChange}
        result={{
          intent: { title: "Generated" },
          key_consistency_report: { prompt_key: "C major", ui_key: "A minor", resolved_key: "A minor", score_document_key: "A minor" },
          score_document: { schema_version: "0.6", title: "Generated", composer: "Sera", global: { key: "A minor" } }
        }}
      />
    );

    expect(screen.getByText("Prompt key")).toBeTruthy();
    expect(screen.getAllByText("A minor").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Edited" } });
    fireEvent.change(screen.getByLabelText("Composer"), { target: { value: "selance" } });
    expect(onMetadataChange).toHaveBeenCalledWith("title", "Edited");
    expect(onMetadataChange).toHaveBeenCalledWith("composer", "selance");
  });
});
