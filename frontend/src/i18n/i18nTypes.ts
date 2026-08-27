export type SupportedLanguage = "en" | "zh-CN";

export type TranslationDictionary = Record<string, string>;

export type I18nContextValue = {
  language: SupportedLanguage;
  setLanguage: (language: SupportedLanguage) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
};
