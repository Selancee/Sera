import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../../i18n";
import AgentPlanPanel from "../AgentPlanPanel.jsx";
import ConsistencyReportPanel from "../ConsistencyReportPanel.jsx";
import ScoreViewer from "../ScoreViewer.jsx";
import ValidationReportPanel from "../ValidationReportPanel.jsx";

function renderWithI18n(ui) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("generated result shape guards", () => {
  it("does not crash when ScoreViewer receives string instrumentation", () => {
    renderWithI18n(
      <ScoreViewer
        onOpenWorkbench={vi.fn()}
        result={{
          intent: { instrumentation: "piano" },
          musicxml: "<score-partwise version=\"3.1\" />",
          run_id: "shape_guard"
        }}
      />
    );

    expect(screen.getByText("Piano")).toBeTruthy();
    expect(screen.getByTestId("real-musicxml-preview")).toBeTruthy();
  });

  it("does not crash when plan lists and report messages are scalar values", () => {
    renderWithI18n(
      <>
        <AgentPlanPanel
          result={{
            plan: {
              agent_plan_json: {
                title: "Shape guard",
                instrumentation: "piano",
                section_plan: { section: "A", measures: "1-4", description: "theme" },
                source_prompt_terms: "cyberpunk",
                plan_grounding: { decision: "texture=ostinato", source: "style_profile_mapper" }
              },
              measures: { index: 1, section: "A", chord: "I" },
              schema_validation: { valid: true }
            }
          }}
        />
        <ConsistencyReportPanel report={{ mismatch_count: 1, warnings: "count mismatch", errors: null }} />
        <ValidationReportPanel result={{ validation_report: { warnings: "review", errors: null } }} />
      </>
    );

    expect(screen.getByText("Shape Guard")).toBeTruthy();
    expect(screen.getByText("count mismatch")).toBeTruthy();
    expect(screen.getByText("review")).toBeTruthy();
  });
});
