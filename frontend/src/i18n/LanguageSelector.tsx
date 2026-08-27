import { useI18n } from "./useI18n";

export default function LanguageSelector() {
  const { language, setLanguage, t } = useI18n();
  return (
    <label className="language-selector">
      <span>{t("language.label")}</span>
      <select value={language} onChange={(event) => setLanguage(event.target.value as "en" | "zh-CN")}>
        <option value="en">{t("language.en")}</option>
        <option value="zh-CN">{t("language.zhCN")}</option>
      </select>
    </label>
  );
}
