import { describe, expect, it } from "vitest";
import { englishSystemText } from "../systemText";
import messages from "../systemMessages.en.json";

describe("English system message presentation", () => {
  it("translates known system messages and retains every diagnostic count", () => {
    for (const [source, english] of Object.entries(messages)) {
      expect(englishSystemText(source)).toBe(english);
      expect(english).not.toMatch(/\p{Script=Han}/u);
    }
    expect(englishSystemText("候选 12")).toBe("Candidate 12");
    expect(englishSystemText("目标选区中的 8 个音符全部位于保护范围内；Sera 未越过保护边界。"))
      .toBe("All 8 target notes are protected. Sera respected the protected scope.");
    expect(englishSystemText("已评审 16 个候选，但全部未通过乐谱事务验证；原谱没有被修改。"))
      .toContain("All 16 reviewed candidates failed transaction validation");
  });

  it("preserves unknown errors, user content, Unicode, and structured payloads", () => {
    const original = Object.freeze({ title: "我的乐谱", instruction: "将选区升高大二度", code: "E11", detail: "外部服务错误：request-123" });
    const snapshot = JSON.stringify(original);
    for (const text of Object.values(original)) expect(englishSystemText(text)).toBe(text);
    expect(englishSystemText(snapshot)).toBe(snapshot);
    expect(JSON.stringify(original)).toBe(snapshot);
    expect(englishSystemText(null)).toBe("");
  });

  it("preserves the underlying error in a recognized diagnostic wrapper", () => {
    expect(englishSystemText("LLM 规划失败，已使用确定性理论计划：HTTP 429 / 请求-123"))
      .toBe("LLM planning failed; using a deterministic theory plan: HTTP 429 / 请求-123");
  });
});
