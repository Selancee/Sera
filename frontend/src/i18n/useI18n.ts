import { useContext } from "react";
import { I18nContext } from "./index";

export function useI18n() {
  return useContext(I18nContext);
}
