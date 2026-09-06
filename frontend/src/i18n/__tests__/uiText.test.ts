import { describe, expect, it } from "vitest";
import chinese from "../locales/ui.zh-CN.json";
import { translateUiText } from "../useUiText";

describe("bilingual interface text", () => {
  it("has nonempty bilingual labels and preserves every interpolation slot", () => {
    for (const [english, translation] of Object.entries(chinese)) {
      expect(english.trim()).not.toBe("");
      expect(translation.trim(), english).not.toBe("");
      expect(translation.match(/\{\d+\}/g) || [], english).toEqual(english.match(/\{\d+\}/g) || []);
      expect(translateUiText(english, "en")).toBe(english);
      expect(translateUiText(english, "zh-CN")).toBe(translation);
    }
  });

  it("translates stored status templates after switching language without changing their values", () => {
    for (const [english, translation] of Object.entries(chinese)) {
      if (!/\{\d+\}/.test(english)) continue;
      const fill = (text: string) => text.replace(/\{(\d+)\}/g, (_, index) => `value-${index}`);
      expect(translateUiText(fill(english), "zh-CN"), english).toBe(fill(translation));
    }
    const status = "LLM refinement complete · Generated 3 candidates";
    expect(translateUiText(status, "zh-CN")).toBe("LLM 优化完成 · 已生成 3 个候选");
    expect(translateUiText(status, "en")).toBe(status);
  });

  it("preserves unknown text and does not replace captured score titles or diagnostic details", () => {
    const text = 'Received from MuseScore Studio: “Apply 我的作品”, host selection M2–M4. You can continue chatting. Switch to Edit proposal to edit the score.';
    expect(translateUiText(text, "zh-CN")).toContain("《Apply 我的作品》");
    const error = "HTTP 429 / request-123 / 原始诊断";
    expect(translateUiText(`Chat request failed: ${error}`, "zh-CN")).toBe(`对话请求失败：${error}`);
    for (const value of ["custom text 我的乐谱", '{"pitch":"C4","duration":"1/3"}']) {
      expect(translateUiText(value, "zh-CN")).toBe(value);
    }
  });
});
