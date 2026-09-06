import { useMemo } from "react";
import { useI18n } from "./useI18n";
import { englishSystemText } from "./systemText";
import chinese from "./locales/ui.zh-CN.json";
import type { SupportedLanguage } from "./i18nTypes";

const messages: Record<string, string> = chinese;
const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const templates = Object.entries(messages)
  .filter(([source]) => /\{\d+\}/.test(source))
  .sort(([left], [right]) => right.replace(/\{\d+\}/g, "").length - left.replace(/\{\d+\}/g, "").length)
  .map(([source, translation]) => {
    const slots: string[] = [];
    const fragments = source.split(/(\{\d+\})/g).map((fragment) => {
      if (/^\{\d+\}$/.test(fragment)) { slots.push(fragment); return "([\\s\\S]*?)"; }
      return escapeRegExp(fragment);
    });
    return { pattern: new RegExp(`^${fragments.join("")}$`), slots, translation };
  });

/** Translate only explicitly selected interface text at render time.
 * Score fields, typed inputs, raw JSON, and provider replies never pass through here.
 */
export function translateUiText(value: string | null | undefined, language: SupportedLanguage): string {
  const source = value ?? "";
  if (language === "en") return source;
  if (Object.hasOwn(messages, source)) return messages[source];
  for (const { pattern, slots, translation } of templates) {
    const match = source.match(pattern);
    if (!match) continue;
    return translation.replace(/\{\d+\}/g, (slot) => match[slots.indexOf(slot) + 1] ?? slot);
  }
  return source;
}

export function useUiText() {
  const { language } = useI18n();
  return useMemo(() => ({
    language,
    ui: (value: string | null | undefined) => translateUiText(value, language),
    systemText: (value: string | null | undefined) => language === "en" ? englishSystemText(value) : (value ?? "")
  }), [language]);
}
