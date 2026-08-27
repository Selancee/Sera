"""Environment-only runtime configuration for the desktop score-editing LLM."""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_: object, **__: object) -> bool:
        return False

from sera_edit.providers.base import LLMProvider
from sera_edit.providers.credential_protection import protect_secret, unprotect_secret
from sera_edit.providers.openai_compatible import OpenAICompatibleProvider
from sera_edit.providers.openai_responses import OpenAIResponsesProvider


LOCAL_PROVIDER_NAMES = {"", "local", "local_rule", "mock", "off", "disabled"}
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai-compatible": "https://api.openai.com/v1",
}
DEFAULT_KEY_ENVS = {
    "openai": ("SERA_LLM_API_KEY", "OPENAI_API_KEY"),
    "deepseek": ("SERA_LLM_API_KEY", "DEEPSEEK_API_KEY"),
    "qwen": ("SERA_LLM_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY"),
    "openai-compatible": ("SERA_LLM_API_KEY", "OPENAI_API_KEY"),
}
MANAGED_ENV_KEYS = {
    "SERA_LLM_PROVIDER",
    "SERA_LLM_MODEL",
    "SERA_LLM_BASE_URL",
    "SERA_LLM_API_KEY",
    "SERA_LLM_API_KEY_ENCRYPTED",
    "SERA_LLM_API_KEY_ENV",
    "SERA_LLM_FALLBACK_LOCAL",
    "SERA_LLM_TIMEOUT_SECONDS",
    "SERA_COMPOSER_LLM_TIMEOUT_SECONDS",
    "SERA_LLM_MAX_OUTPUT_TOKENS",
    "SERA_LLM_REASONING_EFFORT",
    "SERA_LLM_STORE",
    "SERA_LLM_STRUCTURED_OUTPUTS",
}

DEFAULT_COMPOSER_LLM_TIMEOUT_SECONDS = 180.0
MIN_COMPOSER_LLM_TIMEOUT_SECONDS = 30.0
MAX_COMPOSER_LLM_TIMEOUT_SECONDS = 600.0


@dataclass(frozen=True, slots=True)
class LLMRuntimeSettings:
    """Resolved provider settings with no credential value."""

    provider: str
    model: str
    base_url: str
    api_key_env: str
    configured: bool
    available: bool
    transport: str
    fallback_local: bool
    timeout_seconds: float
    max_output_tokens: int
    reasoning_effort: str
    store: bool
    supports_structured_outputs: bool
    input_cost_per_million: float | None
    output_cost_per_million: float | None
    config_file: str
    reason: str

    def public_status(self) -> dict[str, object]:
        """Return user-visible state without API-key material."""

        data = asdict(self)
        data["mode"] = "live_llm" if self.available else "local_rule"
        data["api_key_configured"] = bool(self.api_key_env and os.getenv(self.api_key_env))
        data["credential_storage"] = (
            "windows_dpapi"
            if os.getenv("SERA_LLM_API_KEY_ENCRYPTED")
            else "environment" if data["api_key_configured"] else "none"
        )
        data["in_app_configuration"] = os.name == "nt"
        data["composer_timeout_seconds"] = composer_timeout_seconds()
        return data


def default_llm_env_path() -> Path:
    """Return the stable per-user config path used by packaged Sera."""

    override = os.getenv("SERA_LLM_ENV_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    return base / "Sera" / "llm.env"


def load_llm_environment(project_root: str | Path | None = None) -> Path:
    """Load development and per-user env files without overriding process env."""

    if project_root is not None:
        load_dotenv(Path(project_root) / ".env", override=False)
    user_file = default_llm_env_path()
    if user_file.is_file():
        load_dotenv(user_file, override=True)
        protected_value = os.getenv("SERA_LLM_API_KEY_ENCRYPTED", "").strip()
        if protected_value:
            try:
                os.environ["SERA_LLM_API_KEY"] = unprotect_secret(protected_value)
            except (OSError, RuntimeError, ValueError):
                os.environ.pop("SERA_LLM_API_KEY", None)
    return user_file


def save_runtime_configuration(
    *,
    provider: str,
    model: str = "",
    api_key: str | None = None,
    base_url: str = "",
    fallback_local: bool = True,
    reasoning_effort: str = "low",
    composer_timeout_seconds_value: float | None = None,
) -> LLMRuntimeSettings:
    """Persist UI-supplied settings and activate them without restarting Sera."""

    normalized_provider = provider.strip().lower()
    if normalized_provider in LOCAL_PROVIDER_NAMES:
        return clear_runtime_configuration()
    if normalized_provider not in DEFAULT_BASE_URLS:
        raise ValueError("不支持所选模型服务商。")
    normalized_model = _safe_single_line(model, "模型名称", maximum=200)
    if not normalized_model:
        raise ValueError("请输入模型名称。")
    normalized_url = _validate_base_url(base_url or DEFAULT_BASE_URLS[normalized_provider])
    normalized_effort = reasoning_effort.strip().lower()
    if normalized_effort not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
        raise ValueError("推理强度设置无效。")

    config_path = default_llm_env_path()
    existing = _read_env_values(config_path)
    existing_provider = existing.get("SERA_LLM_PROVIDER", "").strip().lower()
    protected_value = ""
    active_secret = ""
    if api_key is not None and api_key.strip():
        active_secret = _safe_single_line(api_key.strip(), "API Key", maximum=4096)
        protected_value = protect_secret(active_secret)
    elif existing_provider == normalized_provider and existing.get("SERA_LLM_API_KEY_ENCRYPTED"):
        protected_value = existing["SERA_LLM_API_KEY_ENCRYPTED"]
        active_secret = unprotect_secret(protected_value)
    elif os.getenv("SERA_LLM_PROVIDER", "").strip().lower() == normalized_provider:
        active_key_env = _resolve_api_key_env(normalized_provider)
        active_secret = os.getenv(active_key_env, "")
        if not active_secret:
            raise ValueError("请输入该服务商的 API Key。")
        protected_value = protect_secret(active_secret)
    if not active_secret:
        raise ValueError("请输入该服务商的 API Key。")

    existing_composer_timeout = existing.get("SERA_COMPOSER_LLM_TIMEOUT_SECONDS", "").strip()
    if composer_timeout_seconds_value is None:
        try:
            requested_composer_timeout = float(existing_composer_timeout)
        except ValueError:
            requested_composer_timeout = DEFAULT_COMPOSER_LLM_TIMEOUT_SECONDS
    else:
        requested_composer_timeout = float(composer_timeout_seconds_value)
    if not math.isfinite(requested_composer_timeout) or not (
        MIN_COMPOSER_LLM_TIMEOUT_SECONDS
        <= requested_composer_timeout
        <= MAX_COMPOSER_LLM_TIMEOUT_SECONDS
    ):
        raise ValueError("Composer 后台等待时间必须在 30 到 600 秒之间。")

    values = {
        "SERA_LLM_PROVIDER": normalized_provider,
        "SERA_LLM_MODEL": normalized_model,
        "SERA_LLM_BASE_URL": normalized_url,
        "SERA_LLM_API_KEY_ENCRYPTED": protected_value,
        "SERA_LLM_API_KEY_ENV": "SERA_LLM_API_KEY",
        "SERA_LLM_FALLBACK_LOCAL": "true" if fallback_local else "false",
        "SERA_LLM_TIMEOUT_SECONDS": existing.get("SERA_LLM_TIMEOUT_SECONDS", "90"),
        "SERA_COMPOSER_LLM_TIMEOUT_SECONDS": f"{requested_composer_timeout:g}",
        "SERA_LLM_MAX_OUTPUT_TOKENS": existing.get("SERA_LLM_MAX_OUTPUT_TOKENS", "4000"),
        "SERA_LLM_REASONING_EFFORT": normalized_effort,
        "SERA_LLM_STORE": "false",
        "SERA_LLM_STRUCTURED_OUTPUTS": "true" if normalized_provider == "openai" else "false",
    }
    _write_managed_env(config_path, values)
    _activate_managed_environment(values, active_secret)
    return runtime_settings()


def composer_timeout_seconds() -> float:
    """Return the long, non-blocking Composer refinement timeout."""

    raw = os.getenv("SERA_COMPOSER_LLM_TIMEOUT_SECONDS", "").strip()
    try:
        value = float(raw) if raw else DEFAULT_COMPOSER_LLM_TIMEOUT_SECONDS
    except ValueError:
        value = DEFAULT_COMPOSER_LLM_TIMEOUT_SECONDS
    if not math.isfinite(value):
        value = DEFAULT_COMPOSER_LLM_TIMEOUT_SECONDS
    return max(MIN_COMPOSER_LLM_TIMEOUT_SECONDS, min(value, MAX_COMPOSER_LLM_TIMEOUT_SECONDS))


def clear_runtime_configuration() -> LLMRuntimeSettings:
    """Switch to the local rule generator and remove any stored API credential."""

    config_path = default_llm_env_path()
    values = {
        "SERA_LLM_PROVIDER": "local_rule",
        "SERA_LLM_FALLBACK_LOCAL": "true",
    }
    _write_managed_env(config_path, values)
    _activate_managed_environment(values, "")
    return runtime_settings()


def runtime_settings() -> LLMRuntimeSettings:
    """Resolve the current interactive provider configuration."""

    provider = os.getenv("SERA_LLM_PROVIDER", "local_rule").strip().lower()
    config_file = str(default_llm_env_path())
    fallback_local = _env_bool("SERA_LLM_FALLBACK_LOCAL", True)
    if provider in LOCAL_PROVIDER_NAMES:
        return LLMRuntimeSettings(
            provider="local_rule",
            model="seraedit_rule_v1",
            base_url="",
            api_key_env="",
            configured=False,
            available=False,
            transport="local",
            fallback_local=fallback_local,
            timeout_seconds=_env_float("SERA_LLM_TIMEOUT_SECONDS", 90.0),
            max_output_tokens=_env_int("SERA_LLM_MAX_OUTPUT_TOKENS", 4000),
            reasoning_effort=os.getenv("SERA_LLM_REASONING_EFFORT", "low").strip().lower(),
            store=_env_bool("SERA_LLM_STORE", False),
            supports_structured_outputs=False,
            input_cost_per_million=_env_optional_float("SERA_LLM_INPUT_COST_PER_MILLION"),
            output_cost_per_million=_env_optional_float("SERA_LLM_OUTPUT_COST_PER_MILLION"),
            config_file=config_file,
            reason="Live LLM provider is not configured; using the local rule generator.",
        )
    if provider not in DEFAULT_BASE_URLS:
        return _unavailable(provider, "Unsupported SERA_LLM_PROVIDER.", config_file, fallback_local)
    model = os.getenv("SERA_LLM_MODEL", "").strip()
    base_url = os.getenv("SERA_LLM_BASE_URL", DEFAULT_BASE_URLS[provider]).strip()
    api_key_env = _resolve_api_key_env(provider)
    reason = ""
    if not model:
        reason = "SERA_LLM_MODEL is not configured."
    elif not api_key_env or not os.getenv(api_key_env):
        reason = "The configured provider API key is missing."
    transport = "responses" if provider == "openai" else "chat_completions"
    return LLMRuntimeSettings(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
        configured=bool(model),
        available=not reason,
        transport=transport,
        fallback_local=fallback_local,
        timeout_seconds=_env_float("SERA_LLM_TIMEOUT_SECONDS", 90.0),
        max_output_tokens=_env_int("SERA_LLM_MAX_OUTPUT_TOKENS", 4000),
        reasoning_effort=os.getenv("SERA_LLM_REASONING_EFFORT", "low").strip().lower(),
        store=_env_bool("SERA_LLM_STORE", False),
        supports_structured_outputs=provider == "openai" or _env_bool("SERA_LLM_STRUCTURED_OUTPUTS", False),
        input_cost_per_million=_env_optional_float("SERA_LLM_INPUT_COST_PER_MILLION"),
        output_cost_per_million=_env_optional_float("SERA_LLM_OUTPUT_COST_PER_MILLION"),
        config_file=config_file,
        reason=reason or "Live LLM provider is ready.",
    )


def create_runtime_provider(settings: LLMRuntimeSettings | None = None) -> LLMProvider | None:
    """Create the configured provider, or return None for local fallback mode."""

    resolved = settings or runtime_settings()
    if not resolved.available:
        return None
    common = {
        "model": resolved.model,
        "base_url": resolved.base_url,
        "api_key_env": resolved.api_key_env,
        "timeout_seconds": resolved.timeout_seconds,
        "input_cost_per_million": resolved.input_cost_per_million,
        "output_cost_per_million": resolved.output_cost_per_million,
    }
    if resolved.provider == "openai":
        return OpenAIResponsesProvider(
            **common,
            reasoning_effort=resolved.reasoning_effort,
            store=resolved.store,
        )
    return OpenAICompatibleProvider(
        provider=resolved.provider,
        **common,
        supports_structured_outputs=resolved.supports_structured_outputs,
    )


def _resolve_api_key_env(provider: str) -> str:
    explicit = os.getenv("SERA_LLM_API_KEY_ENV", "").strip()
    if explicit:
        return explicit
    candidates = DEFAULT_KEY_ENVS[provider]
    return next((name for name in candidates if os.getenv(name)), candidates[0])


def _safe_single_line(value: str, label: str, *, maximum: int) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"{label} 不能包含换行或空字符。")
    if len(value) > maximum:
        raise ValueError(f"{label} 过长。")
    return value.strip()


def _validate_base_url(value: str) -> str:
    normalized = _safe_single_line(value.strip().rstrip("/"), "API 地址", maximum=500)
    parsed = urlsplit(normalized)
    is_local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme not in ({"http", "https"} if is_local else {"https"}):
        raise ValueError("远程 API 地址必须使用 HTTPS；仅本机地址允许 HTTP。")
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("API 地址格式无效，不能包含凭据、查询参数或片段。")
    return normalized


def _read_env_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _write_managed_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Managed by Sera. The API key below is encrypted for the current Windows user.",
        *(f"{key}={value}" for key, value in values.items()),
        "",
    ]
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    os.replace(temporary, path)


def _activate_managed_environment(values: dict[str, str], api_key: str) -> None:
    for key in MANAGED_ENV_KEYS:
        os.environ.pop(key, None)
    os.environ.update(values)
    if api_key:
        os.environ["SERA_LLM_API_KEY"] = api_key


def _unavailable(provider: str, reason: str, config_file: str, fallback_local: bool) -> LLMRuntimeSettings:
    return LLMRuntimeSettings(
        provider=provider,
        model=os.getenv("SERA_LLM_MODEL", "").strip(),
        base_url=os.getenv("SERA_LLM_BASE_URL", "").strip(),
        api_key_env=os.getenv("SERA_LLM_API_KEY_ENV", "").strip(),
        configured=False,
        available=False,
        transport="unknown",
        fallback_local=fallback_local,
        timeout_seconds=_env_float("SERA_LLM_TIMEOUT_SECONDS", 90.0),
        max_output_tokens=_env_int("SERA_LLM_MAX_OUTPUT_TOKENS", 4000),
        reasoning_effort=os.getenv("SERA_LLM_REASONING_EFFORT", "low").strip().lower(),
        store=_env_bool("SERA_LLM_STORE", False),
        supports_structured_outputs=False,
        input_cost_per_million=None,
        output_cost_per_million=None,
        config_file=config_file,
        reason=reason,
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_optional_float(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
