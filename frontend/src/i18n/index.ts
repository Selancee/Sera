import React, { createContext, useEffect, useMemo, useState } from "react";
import en from "./locales/en.json";
import zhCN from "./locales/zh-CN.json";
import type { I18nContextValue, SupportedLanguage, TranslationDictionary } from "./i18nTypes";

const STORAGE_KEY = "sera.language";
const dictionaries: Record<SupportedLanguage, TranslationDictionary> = {
  en,
  "zh-CN": zhCN
};

export const I18nContext = createContext<I18nContextValue>({
  language: "en",
  setLanguage: () => undefined,
  t: (key) => dictionaries.en[key] || key
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => detectInitialLanguage());

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, language);
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<I18nContextValue>(() => {
    const t = (key: string, values: Record<string, string | number> = {}) => {
      const template = dictionaries[language][key] || dictionaries.en[key] || key;
      return Object.entries(values).reduce((text, [name, replacement]) => text.replaceAll(`{${name}}`, String(replacement)), template);
    };
    return { language, setLanguage: setLanguageState, t };
  }, [language]);

  return React.createElement(I18nContext.Provider, { value }, children);
}

export function supportedLanguages(): SupportedLanguage[] {
  return ["en", "zh-CN"];
}

function detectInitialLanguage(): SupportedLanguage {
  const saved = window.localStorage.getItem(STORAGE_KEY) as SupportedLanguage | null;
  if (saved && saved in dictionaries) return saved;
  return "en";
}
