"""DeepSeek OpenAI-compatible provider adapter."""

from sera_edit.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """Configured DeepSeek adapter."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(provider="deepseek", **kwargs)
