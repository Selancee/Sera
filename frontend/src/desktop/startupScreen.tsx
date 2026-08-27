import { useEffect, useState } from "react";
import { waitForBackendHealth, type BackendHealthResult } from "./backendHealth";
import { isDesktopRuntime, resolveBackendBaseUrl } from "./desktopRuntime";

export function StartupScreen({ children }: { children: React.ReactNode }) {
  const [health, setHealth] = useState<BackendHealthResult | null>(() => (isDesktopRuntime() ? null : { ok: true, baseUrl: resolveBackendBaseUrl(), attempts: 0 }));

  useEffect(() => {
    if (!isDesktopRuntime()) return;
    waitForBackendHealth(resolveBackendBaseUrl).then(setHealth);
  }, []);

  if (!health) {
    return <div className="startup-screen">正在完成 Sera 本地引擎健康检查…</div>;
  }
  if (!health.ok) {
    return <div className="startup-screen error">Sera 本地引擎不可用：{health.error}</div>;
  }
  return <>{children}</>;
}
