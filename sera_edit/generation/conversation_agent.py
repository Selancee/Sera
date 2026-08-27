"""Conversation-only Sera assistant that can never mutate a score."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from backend.services.score_document_service import normalize_score_document
from sera_edit.generation.prompts import compact_score_context
from sera_edit.providers.base import LLMProvider, ProviderRequestError, ProviderResponse
from sera_edit.providers.runtime import LLMRuntimeSettings, create_runtime_provider, runtime_settings


ConversationStatus = Literal["answered", "unavailable"]
CONVERSATION_PROMPT_VERSION = "sera_conversation_v1.0"
MAX_HISTORY_TURNS = 12
MAX_HISTORY_CHARS = 24_000


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """A plain-language answer with provider evidence and no patch payload."""

    status: ConversationStatus
    answer: str
    response: ProviderResponse | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        response = self.response
        return {
            "status": self.status,
            "answer": self.answer,
            "reason": self.reason,
            "generator": {
                "provider": response.provider if response else "local_rule",
                "model": response.model if response else "sera_conversation_unavailable",
                "transport": "responses" if response and response.provider == "openai" else "chat_completions",
                "live": response is not None,
                "prompt_version": CONVERSATION_PROMPT_VERSION,
                "latency_ms": round(response.latency_ms, 3) if response else None,
                "input_tokens": response.input_tokens if response else None,
                "output_tokens": response.output_tokens if response else None,
                "request_id": response.request_id if response else None,
            },
        }


def converse_with_runtime(
    message: str,
    history: list[dict[str, str]] | None = None,
    score_document: dict[str, Any] | None = None,
    target_scope: dict[str, Any] | None = None,
    *,
    settings: LLMRuntimeSettings | None = None,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Answer a normal message without invoking patch generation or execution."""

    resolved = settings or runtime_settings()
    live_provider = provider or create_runtime_provider(resolved)
    if live_provider is None:
        reason = resolved.reason or "Live LLM provider is unavailable."
        result = ConversationResult(
            status="unavailable",
            answer="当前未启用可用的 LLM，对话功能暂不可用。请在“模型设置”中配置服务；本地规则仍可用于受支持的修改指令。",
            reason=reason,
        ).as_dict()
        result["provider_status"] = resolved.public_status()
        return result

    messages = _conversation_messages(message, history or [], score_document, target_scope or {})
    try:
        response = live_provider.generate(
            messages,
            response_schema=None,
            temperature=0.2,
            max_tokens=min(resolved.max_output_tokens, 2000),
        )
    except (ProviderRequestError, ValueError) as exc:
        result = ConversationResult(
            status="unavailable",
            answer="LLM 对话请求失败。乐谱没有发生任何修改。",
            reason=str(exc),
        ).as_dict()
        result["provider_status"] = resolved.public_status()
        return result

    answer = _plain_text(response.raw_text)
    if not answer:
        result = ConversationResult(
            status="unavailable",
            answer="LLM 没有返回可显示的对话内容。乐谱没有发生任何修改。",
            response=response,
            reason="empty_response",
        ).as_dict()
    else:
        result = ConversationResult(status="answered", answer=answer, response=response).as_dict()
    result["provider_status"] = resolved.public_status()
    return result


def _conversation_messages(
    message: str,
    history: list[dict[str, str]],
    score_document: dict[str, Any] | None,
    target_scope: dict[str, Any],
) -> list[dict[str, str]]:
    system_prompt = (
        "You are Sera's conversation assistant for professional music-notation editing. "
        "Answer the user's question in the same language, clearly and concisely. This is a conversation-only channel: "
        "never output ScorePatch JSON or MusicXML, never claim that a score was changed, and never imply that an edit "
        "was applied. If the user gives an edit command, explain that they should use the separate 'Generate edit "
        "proposal' mode, where the server binds scope and validates a structured patch. You may discuss music theory, "
        "the connected score context, Sera usage, or help the user phrase a precise editing instruction."
        " Use plain text without Markdown formatting."
    )
    bounded_history = _bounded_history(history)
    context: dict[str, Any] | None = None
    if score_document is not None:
        score = normalize_score_document(score_document)
        context = compact_score_context(score, target_scope) if target_scope else {
            "score_id": score.get("score_id"),
            "title": score.get("title"),
            "global": score.get("global") or {},
            "measure_count": len(score.get("measures") or []),
        }
    user_content = message.strip()
    if context is not None:
        user_content = json.dumps(
            {"message": user_content, "connected_score_context": context},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return [
        {"role": "system", "content": system_prompt},
        *bounded_history,
        {"role": "user", "content": user_content},
    ]


def _bounded_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    accepted: list[dict[str, str]] = []
    total = 0
    for item in reversed(history[-MAX_HISTORY_TURNS:]):
        role = str(item.get("role", ""))
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        remaining = MAX_HISTORY_CHARS - total
        if remaining <= 0:
            break
        clipped = content[-remaining:]
        accepted.append({"role": role, "content": clipped})
        total += len(clipped)
    accepted.reverse()
    return accepted


def _plain_text(value: str) -> str:
    """Remove common inline Markdown markers unsupported by the desktop message view."""

    text = value.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"\1", text, flags=re.DOTALL)
    return text
