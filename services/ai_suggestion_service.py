from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.settings_service import settings_service


DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"
DEFAULT_TIMEOUT_SECONDS = 30
SUGGESTION_SYSTEM_PROMPT = (
    "You are assisting with qualitative coding. Propose approximately 3 to 5 "
    "concise, useful coding suggestions grounded only in the selected research "
    "text. Suggestions are proposals for researcher review, not final truth. "
    "Reuse a supplied existing NodeFlow node when it fits semantically; only "
    "propose a new code when the existing nodes do not adequately represent "
    "the selected meaning. Do not invent unsupported interpretations. Return "
    "only a JSON object with a suggestions array. Each item must contain name, "
    "reason, and existing_node_id, where existing_node_id is one supplied node "
    "ID or null for a proposed new code."
)


class AISuggestionError(RuntimeError):
    """Base error for safe, user-facing AI suggestion failures."""


class AIConfigurationError(AISuggestionError):
    """Raised when the provider cannot be configured safely."""


class AIProviderError(AISuggestionError):
    """Raised when the provider request cannot be completed."""


class AIResponseError(AISuggestionError):
    """Raised when the provider response fails schema validation."""


@dataclass(frozen=True)
class AISuggestion:
    name: str
    reason: str
    existing_node_id: int | None


Transport = Callable[[Request, float], bytes | str | dict[str, Any]]


class SuggestionProvider(Protocol):
    def request(
        self, selected_text: str, node_context: list[dict[str, Any]]
    ) -> dict[str, Any]: ...


def _saved_settings() -> dict[str, Any]:
    return settings_service.load()


def _configured_value(
    settings: dict[str, Any],
    environment_name: str,
    setting_name: str,
    default: str | None = None,
) -> str | None:
    environment_value = os.getenv(environment_name)
    if environment_value and environment_value.strip():
        return environment_value
    setting_value = settings.get(setting_name)
    if isinstance(setting_value, str) and setting_value.strip():
        return setting_value
    return default


def _urlopen_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _decode_json_response(
    raw_response: bytes | str | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(raw_response, dict):
        return raw_response
    if isinstance(raw_response, bytes):
        try:
            raw_response = raw_response.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AIResponseError("The AI provider returned invalid JSON.") from exc
    if not isinstance(raw_response, str):
        raise AIResponseError("The AI provider returned invalid JSON.")
    try:
        response = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise AIResponseError("The AI provider returned invalid JSON.") from exc
    if not isinstance(response, dict):
        raise AIResponseError("The AI provider returned an invalid response.")
    return response


class OpenAICompatibleProvider:
    """Small replaceable provider for OpenAI-compatible chat-completions APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Transport | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        settings = _saved_settings() if settings is None else settings
        self.api_key = api_key if api_key is not None else _configured_value(
            settings, "NODEFLOW_AI_API_KEY", "ai_api_key"
        )
        self.api_url = api_url or _configured_value(
            settings, "NODEFLOW_AI_API_URL", "ai_api_url", DEFAULT_API_URL
        )
        self.model = model or _configured_value(
            settings, "NODEFLOW_AI_MODEL", "ai_model", DEFAULT_MODEL
        )
        self.timeout = timeout
        self.transport = transport or _urlopen_transport

    def request(
        self, selected_text: str, node_context: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIConfigurationError(
                "Configure an AI API key in Settings or set NODEFLOW_AI_API_KEY."
            )

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": SUGGESTION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "selected_text": selected_text,
                            "existing_nodes": node_context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        try:
            request = Request(
                self.api_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            raw_response = self.transport(request, self.timeout)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            raise AIProviderError("The AI provider request failed.") from exc

        return _decode_json_response(raw_response)


class GeminiProvider:
    """Native Gemini generateContent provider."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: Transport | None = None,
        settings: dict[str, Any] | None = None,
    ) -> None:
        settings = _saved_settings() if settings is None else settings
        self.api_key = api_key if api_key is not None else _configured_value(
            settings, "NODEFLOW_AI_API_KEY", "ai_api_key"
        )
        self.model = model or _configured_value(
            settings, "NODEFLOW_AI_MODEL", "ai_model", DEFAULT_GEMINI_MODEL
        )
        api_url_template = api_url or _configured_value(
            settings,
            "NODEFLOW_GEMINI_API_URL",
            "ai_api_url",
            DEFAULT_GEMINI_API_URL,
        )
        self.api_url = api_url_template.replace("{model}", self.model)
        self.timeout = timeout
        self.transport = transport or _urlopen_transport

    def request(
        self, selected_text: str, node_context: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIConfigurationError(
                "Configure an AI API key in Settings or set NODEFLOW_AI_API_KEY."
            )

        payload = {
            "systemInstruction": {
                "parts": [{"text": SUGGESTION_SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "selected_text": selected_text,
                                    "existing_nodes": node_context,
                                },
                                ensure_ascii=False,
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        try:
            request = Request(
                self.api_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                },
                method="POST",
            )
            raw_response = self.transport(request, self.timeout)
        except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
            raise AIProviderError("The AI provider request failed.") from exc

        response = _decode_json_response(raw_response)
        try:
            parts = response["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("The AI provider returned no suggestions.") from exc
        text_parts = [part["text"] for part in parts if isinstance(part, dict) and "text" in part]
        if not text_parts:
            raise AIResponseError("The AI provider returned no suggestions.")
        try:
            structured_response = json.loads("".join(text_parts))
        except json.JSONDecodeError as exc:
            raise AIResponseError("The AI provider returned invalid JSON.") from exc
        if not isinstance(structured_response, dict):
            raise AIResponseError("The AI provider returned an invalid response.")
        return structured_response


class AISuggestionService:
    def __init__(self, provider: SuggestionProvider | None = None) -> None:
        self.provider = provider or self._create_default_provider()

    @staticmethod
    def _create_default_provider() -> SuggestionProvider:
        settings = _saved_settings()
        provider_name = _configured_value(
            settings, "NODEFLOW_AI_PROVIDER", "ai_provider", "gemini"
        ).strip().lower()
        if provider_name in {"gemini", "google"}:
            return GeminiProvider(settings=settings)
        if provider_name in {"openai", "openai_compatible"}:
            return OpenAICompatibleProvider(settings=settings)
        raise AIConfigurationError(f"Unsupported AI provider: {provider_name}.")

    def suggest(
        self, selected_text: str, node_context: list[dict[str, Any]]
    ) -> list[AISuggestion]:
        if not isinstance(selected_text, str) or not selected_text.strip():
            raise AIResponseError("Selected text is empty.")
        valid_node_ids = self._validate_node_context(node_context)
        response = self.provider.request(selected_text, node_context)
        return self.parse_response(response, valid_node_ids)

    @classmethod
    def parse_response(
        cls, response: dict[str, Any], valid_node_ids: set[int]
    ) -> list[AISuggestion]:
        content: Any = response
        if not isinstance(response, dict):
            raise AIResponseError("The AI provider returned an invalid response.")
        if "suggestions" not in response:
            try:
                content = response["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise AIResponseError("The AI provider response is missing suggestions.") from exc

        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as exc:
                raise AIResponseError("The AI provider returned invalid JSON.") from exc
        if not isinstance(content, dict) or not isinstance(
            content.get("suggestions"), list
        ):
            raise AIResponseError("The AI provider response is missing suggestions.")

        suggestions = []
        seen: set[tuple[str, int | None]] = set()
        for item in content["suggestions"]:
            if not isinstance(item, dict):
                raise AIResponseError("The AI provider returned an invalid suggestion.")
            name = item.get("name")
            reason = item.get("reason")
            existing_node_id = item.get("existing_node_id")
            if not isinstance(name, str) or not name.strip():
                raise AIResponseError("The AI provider returned an empty suggestion name.")
            if not isinstance(reason, str):
                raise AIResponseError("The AI provider returned an invalid suggestion reason.")
            if (
                isinstance(existing_node_id, bool)
                or (
                    existing_node_id is not None
                    and (
                        not isinstance(existing_node_id, int)
                        or existing_node_id not in valid_node_ids
                    )
                )
            ):
                raise AIResponseError(
                    "AI suggestions must reference an existing node or null."
                )
            dedupe_key = (name.strip().casefold(), existing_node_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            suggestions.append(
                AISuggestion(
                    name=name.strip(),
                    reason=reason.strip(),
                    existing_node_id=existing_node_id,
                )
            )
        return suggestions

    @staticmethod
    def _validate_node_context(node_context: list[dict[str, Any]]) -> set[int]:
        if not isinstance(node_context, list):
            raise AIResponseError("Node context is invalid.")
        valid_node_ids = set()
        for node in node_context:
            if not isinstance(node, dict):
                raise AIResponseError("Node context is invalid.")
            node_id = node.get("id")
            if isinstance(node_id, bool) or not isinstance(node_id, int):
                raise AIResponseError("Node context is invalid.")
            valid_node_ids.add(node_id)
        return valid_node_ids
