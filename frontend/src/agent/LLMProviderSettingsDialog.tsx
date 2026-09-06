import { useUiText } from "../i18n/useUiText";
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
  const { ui, language, systemText } = useUiText();
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
      setError(caught?.message || "Could not save model settings. Check the provider, model, and API key.");
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
      setError(caught?.message || "Could not switch to local rules.");
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
            <span>{ui("Agent runtime")}</span>
            <h1 id="llm-settings-title">{ui("Model and API settings")}</h1>
          </div>
          <button aria-label={ui("Close model settings")} disabled={saving} onClick={onClose} type="button">×</button>
        </header>

        <form onSubmit={handleSubmit}>
          <label> {ui("Model provider")} <select
              aria-label={ui("Model provider")}
              disabled={saving}
              onChange={(event) => handleProviderChange(event.target.value as ProviderId)}
              value={provider}
            >
              <option value="openai">{ui("OpenAI")}</option>
              <option value="deepseek">{ui("DeepSeek")}</option>
              <option value="qwen">{ui("Qwen")}</option>
              <option value="openai-compatible">{ui("OpenAI-compatible API")}</option>
            </select>
          </label>

          <label> {ui("Model name")} <input
              aria-label={ui("Model name")}
              autoComplete="off"
              disabled={saving}
              onChange={(event) => setModel(event.target.value)}
              placeholder={ui("For example: gpt-5.6-terra")}
              required
              value={model}
            />
          </label>

          <label> {ui("API URL")} <input
              aria-label={ui("API URL")}
              autoCapitalize="none"
              autoComplete="off"
              disabled={saving}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder={ui("https://api.example.com/v1")}
              required
              spellCheck={false}
              type="url"
              value={baseUrl}
            />
          </label>

          <label> {ui("API Key")} <input
              aria-describedby="api-key-storage-note"
              aria-label={ui("API Key")}
              autoCapitalize="none"
              autoComplete="new-password"
              disabled={saving}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={ui(canRetainCredential ? "Saved securely; leave blank to keep" : "Paste API key")}
              required={!canRetainCredential}
              spellCheck={false}
              type="password"
              value={apiKey}
            />
          </label>

          <p className="agent-credential-note" id="api-key-storage-note"> {ui("The key is encrypted for the current Windows user. It is never displayed in the interface, status API, or conversation history.")} </p>

          <div className="agent-settings-row">
            <label> {ui("Reasoning effort")} <select
                aria-label={ui("Reasoning effort")}
                disabled={saving}
                onChange={(event) => setReasoningEffort(event.target.value)}
                value={reasoningEffort}
              >
                <option value="minimal">{ui("Minimal")}</option>
                <option value="low">{ui("Low")}</option>
                <option value="medium">{ui("Medium")}</option>
                <option value="high">{ui("High")}</option>
              </select>
            </label>
            <label className="agent-settings-check">
              <input
                checked={fallbackLocal}
                disabled={saving}
                onChange={(event) => setFallbackLocal(event.target.checked)}
                type="checkbox"
              /> {ui("Use local rules if the API fails")} </label>
          </div>

          <label> {ui("Composer background timeout (seconds)")} <input
              aria-describedby="composer-timeout-note"
              aria-label={ui("Composer background timeout in seconds")}
              disabled={saving}
              max={600}
              min={30}
              onChange={(event) => setComposerTimeoutSeconds(Number(event.target.value))}
              step={30}
              type="number"
              value={composerTimeoutSeconds}
            />
          </label>
          <p className="agent-credential-note" id="composer-timeout-note"> {ui("This timeout applies to background planning; local candidates remain available. Allow 180–300 seconds for slower reasoning models such as DeepSeek V4 Pro.")} </p>

          {error && <p className="agent-settings-error" role="alert">{ui(error)}</p>}

          <footer>
            <button className="secondary" disabled={saving} onClick={handleUseLocalRules} type="button"> {ui("Use local rules")} </button>
            <div>
              <button className="secondary" disabled={saving} onClick={onClose} type="button">{ui("Cancel")}</button>
              <button
                disabled={saving || !model.trim() || !baseUrl.trim() || composerTimeoutSeconds < 30 || composerTimeoutSeconds > 600}
                type="submit"
              >
                {ui(saving ? "Saving securely…" : "Save and enable")}
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
