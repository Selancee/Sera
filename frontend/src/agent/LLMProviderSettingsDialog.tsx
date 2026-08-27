import { useEffect, useState, type FormEvent } from "react";
import {
  clearSeraEditProviderConfiguration,
  saveSeraEditProviderConfiguration
} from "../api.js";

export type ProviderStatus = {
  mode: "live_llm" | "local_rule";
  provider: string;
  model: string;
  base_url?: string;
  available: boolean;
  configured?: boolean;
  api_key_configured?: boolean;
  credential_storage?: "windows_dpapi" | "environment" | "none";
  in_app_configuration?: boolean;
  transport: string;
  fallback_local?: boolean;
  reasoning_effort?: string;
  timeout_seconds?: number;
  composer_timeout_seconds?: number;
  reason: string;
};

type ProviderId = "openai" | "deepseek" | "qwen" | "openai-compatible";

const PROVIDER_DEFAULTS: Record<ProviderId, { model: string; baseUrl: string }> = {
  openai: { model: "gpt-5.6-terra", baseUrl: "https://api.openai.com/v1" },
  deepseek: { model: "deepseek-chat", baseUrl: "https://api.deepseek.com/v1" },
  qwen: { model: "qwen-plus", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  "openai-compatible": { model: "", baseUrl: "" }
};

export default function LLMProviderSettingsDialog({
  currentStatus,
  onClose,
  onSaved
}: {
  currentStatus: ProviderStatus | null;
  onClose: () => void;
  onSaved: (status: ProviderStatus) => void;
}) {
  const hasRemoteConfiguration = Boolean(currentStatus && isRemoteProvider(currentStatus.provider));
  const initialProvider = hasRemoteConfiguration
    ? currentStatus!.provider as ProviderId
    : "openai";
  const defaults = PROVIDER_DEFAULTS[initialProvider];
  const [provider, setProvider] = useState<ProviderId>(initialProvider);
  const [model, setModel] = useState(hasRemoteConfiguration ? currentStatus?.model || defaults.model : defaults.model);
  const [baseUrl, setBaseUrl] = useState(hasRemoteConfiguration ? currentStatus?.base_url || defaults.baseUrl : defaults.baseUrl);
  const [apiKey, setApiKey] = useState("");
  const [fallbackLocal, setFallbackLocal] = useState(currentStatus?.fallback_local ?? true);
  const [reasoningEffort, setReasoningEffort] = useState(currentStatus?.reasoning_effort || "low");
  const [composerTimeoutSeconds, setComposerTimeoutSeconds] = useState(
    Math.round(currentStatus?.composer_timeout_seconds || 180)
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const canRetainCredential = Boolean(
    currentStatus?.api_key_configured && currentStatus.provider === provider
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, saving]);

  function handleProviderChange(nextProvider: ProviderId) {
    setProvider(nextProvider);
    setModel(PROVIDER_DEFAULTS[nextProvider].model);
    setBaseUrl(PROVIDER_DEFAULTS[nextProvider].baseUrl);
    setApiKey("");
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = await saveSeraEditProviderConfiguration({
        provider,
        model: model.trim(),
        base_url: baseUrl.trim(),
        api_key: apiKey.trim() || null,
        fallback_local: fallbackLocal,
        reasoning_effort: reasoningEffort,
        composer_timeout_seconds: composerTimeoutSeconds
      });
      setApiKey("");
      onSaved(payload.status as ProviderStatus);
      onClose();
    } catch (caught: any) {
      setApiKey("");
      setError(caught?.message || "模型配置保存失败。请检查服务商、模型和 API Key。");
    } finally {
      setSaving(false);
    }
  }

  async function handleUseLocalRules() {
    setSaving(true);
    setError("");
    try {
      const payload = await clearSeraEditProviderConfiguration();
      setApiKey("");
      onSaved(payload.status as ProviderStatus);
      onClose();
    } catch (caught: any) {
      setError(caught?.message || "无法切换到本地规则。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="agent-settings-backdrop" role="presentation">
      <section
        aria-labelledby="llm-settings-title"
        aria-modal="true"
        className="agent-settings-dialog"
        role="dialog"
      >
        <header>
          <div>
            <span>Agent runtime</span>
            <h1 id="llm-settings-title">模型与 API 设置</h1>
          </div>
          <button aria-label="关闭模型设置" disabled={saving} onClick={onClose} type="button">×</button>
        </header>

        <form onSubmit={handleSubmit}>
          <label>
            模型服务商
            <select
              aria-label="模型服务商"
              disabled={saving}
              onChange={(event) => handleProviderChange(event.target.value as ProviderId)}
              value={provider}
            >
              <option value="openai">OpenAI</option>
              <option value="deepseek">DeepSeek</option>
              <option value="qwen">通义千问（Qwen）</option>
              <option value="openai-compatible">OpenAI 兼容接口</option>
            </select>
          </label>

          <label>
            模型名称
            <input
              aria-label="模型名称"
              autoComplete="off"
              disabled={saving}
              onChange={(event) => setModel(event.target.value)}
              placeholder="例如 gpt-5.6-terra"
              required
              value={model}
            />
          </label>

          <label>
            API 地址
            <input
              aria-label="API 地址"
              autoCapitalize="none"
              autoComplete="off"
              disabled={saving}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="https://api.example.com/v1"
              required
              spellCheck={false}
              type="url"
              value={baseUrl}
            />
          </label>

          <label>
            API Key
            <input
              aria-describedby="api-key-storage-note"
              aria-label="API Key"
              autoCapitalize="none"
              autoComplete="new-password"
              disabled={saving}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={canRetainCredential ? "已安全保存；留空则保留" : "粘贴 API Key"}
              required={!canRetainCredential}
              spellCheck={false}
              type="password"
              value={apiKey}
            />
          </label>

          <p className="agent-credential-note" id="api-key-storage-note">
            密钥由 Windows 当前用户加密保存。界面、状态接口和对话记录均不会回显密钥。
          </p>

          <div className="agent-settings-row">
            <label>
              推理强度
              <select
                aria-label="推理强度"
                disabled={saving}
                onChange={(event) => setReasoningEffort(event.target.value)}
                value={reasoningEffort}
              >
                <option value="minimal">Minimal</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className="agent-settings-check">
              <input
                checked={fallbackLocal}
                disabled={saving}
                onChange={(event) => setFallbackLocal(event.target.checked)}
                type="checkbox"
              />
              API 失败时自动使用本地规则
            </label>
          </div>

          <label>
            Composer 后台等待（秒）
            <input
              aria-describedby="composer-timeout-note"
              aria-label="Composer 后台等待秒数"
              disabled={saving}
              max={600}
              min={30}
              onChange={(event) => setComposerTimeoutSeconds(Number(event.target.value))}
              step={30}
              type="number"
              value={composerTimeoutSeconds}
            />
          </label>
          <p className="agent-credential-note" id="composer-timeout-note">
            只限制后台高层规划，不会阻塞本地候选。DeepSeek V4 Pro 等慢推理模型建议 180–300 秒。
          </p>

          {error && <p className="agent-settings-error" role="alert">{error}</p>}

          <footer>
            <button className="secondary" disabled={saving} onClick={handleUseLocalRules} type="button">
              使用本地规则
            </button>
            <div>
              <button className="secondary" disabled={saving} onClick={onClose} type="button">取消</button>
              <button
                disabled={saving || !model.trim() || !baseUrl.trim() || composerTimeoutSeconds < 30 || composerTimeoutSeconds > 600}
                type="submit"
              >
                {saving ? "正在安全保存…" : "保存并启用"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}

function isRemoteProvider(value: string | undefined): value is ProviderId {
  return value === "openai"
    || value === "deepseek"
    || value === "qwen"
    || value === "openai-compatible";
}
