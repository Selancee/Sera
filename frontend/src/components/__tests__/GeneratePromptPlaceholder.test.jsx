import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../../i18n";
import PromptInput from "../PromptInput.jsx";

const params = {
  style: "romantic",
  instrument: "piano",
  key: "A minor",
  meter: "4/4",
  length: 16,
  difficulty: "intermediate",
  rhythmic_density: "medium",
  texture: "melody_accompaniment",
  accompaniment_style: "bass_chord",
  cadence_strength: "clear",
  generator_mode: "hybrid_v05",
  model_task_type: "melody_fragment",
  tempo: 84
};

function renderPromptInput(props = {}) {
  return render(
    <I18nProvider>
      <PromptInput
        controlOnly
        disabled={false}
        onGenerate={vi.fn()}
        params={params}
        prompt=""
        setParams={vi.fn()}
        setPrompt={vi.fn()}
        {...props}
      />
    </I18nProvider>
  );
}

describe("Generate prompt placeholder", () => {
  it("uses placeholder text without a default prompt value", () => {
    renderPromptInput();
    const textbox = screen.getByRole("textbox", { name: /prompt/i });

    expect(textbox.value).toBe("");
    expect(textbox.getAttribute("placeholder")).toContain("Describe the music");
    expect(textbox.getAttribute("placeholder")).not.toBe(textbox.value);
    expect(screen.getByText("Generating from controls only")).toBeTruthy();
  });

  it("allows generation with an empty prompt when controls are present", () => {
    const onGenerate = vi.fn();
    renderPromptInput({ onGenerate });

    fireEvent.click(screen.getByRole("button", { name: /generate/i }));

    expect(onGenerate).toHaveBeenCalledTimes(1);
  });
});
