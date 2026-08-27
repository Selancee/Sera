import { describe, expect, it } from "vitest";
import en from "../locales/en.json";
import zhCN from "../locales/zh-CN.json";

describe("translation coverage", () => {
  it("keeps English and Simplified Chinese locale keys in sync", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(zhCN).sort());
  });

  it("does not contain empty translation values", () => {
    for (const [key, value] of Object.entries({ ...en, ...zhCN })) {
      expect(String(value).trim(), key).not.toBe("");
    }
  });
});
