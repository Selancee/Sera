import type { I18nContextValue } from "./i18nTypes";

export type Translate = I18nContextValue["t"];

export function normalizeTerm(value: string | number | boolean | null | undefined) {
  return String(value ?? "")
    .trim()
    .replaceAll("%", "percent")
    .replaceAll("+", "plus")
    .replaceAll("-", "_")
    .replaceAll("/", "_")
    .replaceAll(" ", "_")
    .replaceAll(".", "_")
    .toLowerCase();
}

export function formatMusicTerm(value: unknown, t: Translate): string {
  if (Array.isArray(value)) return value.map((item) => formatMusicTerm(item, t)).join(", ");
  if (typeof value === "boolean") return t(value ? "common.yes" : "common.no");
  if (value === null || value === undefined || value === "") return t("workbench.none");
  const key = `musicTerm.${normalizeTerm(String(value))}`;
  const translated = t(key);
  return translated === key ? humanize(String(value)) : translated;
}

export function formatFieldLabel(value: string, t: Translate): string {
  const key = `field.${normalizeTerm(value)}`;
  const translated = t(key);
  return translated === key ? humanize(value) : translated;
}

export function formatDuration(value: string, t: Translate): string {
  const key = `duration.${normalizeTerm(value)}`;
  const translated = t(key);
  return translated === key ? humanize(value) : translated;
}

export function durationSymbol(value: string): string {
  return (
    {
      whole: "𝅝",
      half: "𝅗𝅥",
      quarter: "♩",
      eighth: "♪",
      sixteenth: "♬",
      dotted_half: "𝅗𝅥.",
      dotted_quarter: "♩.",
      dotted_eighth: "♪.",
      triplet_eighth: "3♪",
      rest: "𝄽"
    } as Record<string, string>
  )[value] || humanize(value);
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
