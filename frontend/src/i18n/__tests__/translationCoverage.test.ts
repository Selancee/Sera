import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import en from "../locales/en.json";
import zhCN from "../locales/zh-CN.json";

describe("translation coverage", () => {
  it("keeps English and Simplified Chinese locale keys in sync", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(zhCN).sort());
  });

  it("does not contain empty translation values", () => {
    for (const dictionary of [en, zhCN]) {
      for (const [key, value] of Object.entries(dictionary)) {
        expect(String(value).trim(), key).not.toBe("");
      }
    }
  });

  it("keeps the English dictionary free of Chinese UI text", () => {
    for (const [key, value] of Object.entries(en)) expect(value, key).not.toMatch(/\p{Script=Han}/u);
  });

  it("prevents untranslated Chinese labels in frontend and desktop source", () => {
    const sourceRoot = resolve("src");
    const untranslated: string[] = [];
    function scan(directory: string) {
      for (const entry of readdirSync(directory, { withFileTypes: true })) {
        if (entry.name === "__tests__" || entry.name === "locales") continue;
        const path = join(directory, entry.name);
        if (entry.isDirectory()) { scan(path); continue; }
        if (!/\.[jt]sx?$/.test(entry.name)) continue;
        // Explicit, display-only mapping of backend messages; never score content.
        if (entry.name === "systemText.ts") continue;
        const contents = readFileSync(path, "utf8");
        contents.split("\n").forEach((line, index) => {
          // Preserve parsing of measure labels from imported Chinese scores.
          if (entry.name === "ScoreCanvas.tsx" && line.includes("text.match(/(?:Measure|")) return;
          if (/\p{Script=Han}/u.test(line)) untranslated.push(`${relative(sourceRoot, path)}:${index + 1}`);
        });
      }
    }
    scan(sourceRoot);
    const shell = readFileSync(join(sourceRoot, "../../electron/main.js"), "utf8");
    expect(shell).toContain('<html lang="en">');
    expect(shell).not.toMatch(/\p{Script=Han}/u);
    expect(untranslated).toEqual([]);
  });
});
