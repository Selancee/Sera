import { useUiText } from "../i18n/useUiText";
import { useEffect, useState } from "react";
import { waitForBackendHealth, type BackendHealthResult } from "./backendHealth";
import { isDesktopRuntime, resolveBackendBaseUrl } from "./desktopRuntime";

export function StartupScreen({ children }: { children: React.ReactNode }) {
  const { ui, language, systemText } = useUiText();
  const [health, setHealth] = useState<BackendHealthResult | null>(() => (isDesktopRuntime() ? null : { ok: true, baseUrl: resolveBackendBaseUrl(), attempts: 0 }));

  useEffect(() => {
    if (!isDesktopRuntime()) return;
    waitForBackendHealth(resolveBackendBaseUrl).then(setHealth);
  }, []);

  if (!health) {
    return <div className="startup-screen">{ui("Checking the Sera local engine…")}</div>;
  }
  if (!health.ok) {
    return <div className="startup-screen error">{ui("Sera local engine unavailable:")} {health.error}</div>;
  }
  return <>{children}</>;
}
