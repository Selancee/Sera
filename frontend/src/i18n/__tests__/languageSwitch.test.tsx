import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
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

  afterEach(() => vi.restoreAllMocks());

  it("defaults to English on a Chinese OS without changing saved user data", () => {
    vi.spyOn(window.navigator, "language", "get").mockReturnValue("zh-CN");
    window.localStorage.setItem("sera.test.score", '{"title":"我的乐谱","pitch":60}');
    render(<I18nProvider><LanguageSelector /><Probe /></I18nProvider>);
    expect(screen.getByText("Generate")).toBeTruthy();
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem("sera.test.score")).toBe('{"title":"我的乐谱","pitch":60}');
  });

  it("retains an explicitly saved language preference", () => {
    window.localStorage.setItem("sera.language", "zh-CN");
    render(<I18nProvider><Probe /></I18nProvider>);
    expect(screen.getByText("生成")).toBeTruthy();
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
