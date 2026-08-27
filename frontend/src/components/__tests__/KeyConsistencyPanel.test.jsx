import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import KeyConsistencyPanel from "../KeyConsistencyPanel.jsx";

describe("KeyConsistencyPanel", () => {
  it("warns when title key is stale", () => {
    render(
      <KeyConsistencyPanel
        report={{
          valid: false,
          prompt_key: "C major",
          ui_key: "A minor",
          resolved_key: "A minor",
          score_document_key: "A minor",
          musicxml_key: "A minor",
          title_key: "C major",
          stale_key_in_title: true,
          warnings: [],
          errors: []
        }}
      />
    );

    expect(screen.getByText(/title appears to reference C major/i)).toBeTruthy();
  });
});
