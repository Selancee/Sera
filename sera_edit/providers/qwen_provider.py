"""Qwen/DashScope OpenAI-compatible provider adapter."""

from sera_edit.providers.openai_compatible import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    """Configured Qwen adapter."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(provider="qwen", **kwargs)
