"""OpenAI Chat Completions provider adapter."""

from sera_edit.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Configured OpenAI adapter."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(provider="openai", **kwargs)
