import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { I18nProvider } from "../index";
import LanguageSelector from "../LanguageSelector";
import { useI18n } from "../useI18n";

function Probe() {
  const { t } = useI18n();
  return <span>{t("mode.generate") || t("prompt.generate")}</span>;
}

describe("language switching", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("updates visible labels and persists the preference", () => {
    render(
      <I18nProvider>
        <LanguageSelector />
        <Probe />
      </I18nProvider>
    );

    fireEvent.change(screen.getByLabelText(/Language/i), { target: { value: "zh-CN" } });

    expect(screen.getByText("生成")).toBeTruthy();
    expect(window.localStorage.getItem("sera.language")).toBe("zh-CN");
  });
});
