import json
from urllib.error import URLError

import pytest

import database
from repositories.base import initialize_database
from services.ai_suggestion_service import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    AISuggestionService,
    DEFAULT_GEMINI_MODEL,
    GeminiProvider,
    OpenAICompatibleProvider,
)
from services.settings_service import settings_service
from utils import app_paths


NODE_CONTEXT = [
    {"id": 7, "name": "Trust", "parent_id": None},
    {"id": 8, "name": "Barriers", "parent_id": 7},
]


def _service(response, api_key="test-key"):
    provider = OpenAICompatibleProvider(
        api_key=api_key,
        transport=lambda request, timeout: response,
    )
    return AISuggestionService(provider)


def test_valid_response_parsing_from_provider_envelope():
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "suggestions": [
                                {
                                    "name": "  Trust  ",
                                    "reason": " A short reason ",
                                    "existing_node_id": 7,
                                },
                                {
                                    "name": "New code",
                                    "reason": "Another reason",
                                    "existing_node_id": 8,
                                },
                            ]
                        }
                    )
                }
            }
        ]
    }

    suggestions = _service(response).suggest("selected text", NODE_CONTEXT)

    assert suggestions[0].name == "Trust"
    assert suggestions[0].reason == "A short reason"
    assert suggestions[0].existing_node_id == 7
    assert suggestions[1].existing_node_id == 8


def test_malformed_json_fails_safely():
    response = {"choices": [{"message": {"content": "not json"}}]}

    with pytest.raises(AIResponseError):
        _service(response).suggest("selected text", NODE_CONTEXT)


def test_missing_suggestions_fails_safely():
    response = {"choices": [{"message": {"content": "{}"}}]}

    with pytest.raises(AIResponseError):
        _service(response).suggest("selected text", NODE_CONTEXT)


def test_empty_suggestion_name_fails_safely():
    response = {
        "suggestions": [{"name": "  ", "reason": "reason", "existing_node_id": 7}]
    }

    with pytest.raises(AIResponseError):
        _service(response).suggest("selected text", NODE_CONTEXT)


def test_invalid_existing_node_id_fails_safely():
    response = {
        "suggestions": [
            {"name": "Code", "reason": "reason", "existing_node_id": 999}
        ]
    }

    with pytest.raises(AIResponseError):
        _service(response).suggest("selected text", NODE_CONTEXT)


def test_missing_existing_node_id_fails_safely():
    response = {
        "suggestions": [{"name": "Code", "reason": "reason", "existing_node_id": None}]
    }

    with pytest.raises(AIResponseError):
        _service(response).suggest("selected text", NODE_CONTEXT)


def test_missing_api_key_does_not_call_provider(monkeypatch):
    monkeypatch.delenv("NODEFLOW_AI_API_KEY", raising=False)
    service = AISuggestionService(OpenAICompatibleProvider(api_key=None))

    with pytest.raises(AIConfigurationError):
        service.suggest("selected text", NODE_CONTEXT)


def test_provider_network_error_is_safe():
    def failing_transport(request, timeout):
        raise URLError("private transport details")

    service = AISuggestionService(
        OpenAICompatibleProvider(api_key="test-key", transport=failing_transport)
    )

    with pytest.raises(AIProviderError):
        service.suggest("selected text", NODE_CONTEXT)


def test_gemini_provider_builds_native_request_and_parses_json():
    captured = {}
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "suggestions": [
                                        {
                                            "name": "Access barriers",
                                            "reason": "Transport limited access.",
                                            "existing_node_id": 7,
                                        }
                                    ]
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }

    def transport(request, timeout):
        captured["url"] = request.full_url
        captured["api_key"] = request.get_header("X-goog-api-key")
        captured["payload"] = json.loads(request.data)
        return response

    provider = GeminiProvider(
        api_key="test-key",
        model="gemini-test",
        transport=transport,
    )

    suggestions = AISuggestionService(provider).suggest(
        "selected text", NODE_CONTEXT
    )

    assert captured["url"].endswith("/models/gemini-test:generateContent")
    assert captured["api_key"] == "test-key"
    assert captured["payload"]["generationConfig"]["responseMimeType"] == (
        "application/json"
    )
    user_payload = json.loads(
        captured["payload"]["contents"][0]["parts"][0]["text"]
    )
    assert user_payload["selected_text"] == "selected text"
    assert suggestions[0].existing_node_id == 7


def test_gemini_malformed_structured_response_fails_safely():
    response = {
        "candidates": [
            {"content": {"parts": [{"text": "not json"}]}}
        ]
    }
    provider = GeminiProvider(
        api_key="test-key",
        transport=lambda request, timeout: response,
    )

    with pytest.raises(AIResponseError):
        AISuggestionService(provider).suggest("selected text", NODE_CONTEXT)


def test_gemini_missing_api_key_does_not_call_provider(monkeypatch):
    monkeypatch.delenv("NODEFLOW_AI_API_KEY", raising=False)
    service = AISuggestionService(GeminiProvider(api_key=None))

    with pytest.raises(AIConfigurationError):
        service.suggest("selected text", NODE_CONTEXT)


def test_gemini_is_the_default_provider(monkeypatch):
    monkeypatch.delenv("NODEFLOW_AI_PROVIDER", raising=False)
    monkeypatch.setenv("NODEFLOW_AI_API_KEY", "test-key")

    service = AISuggestionService()

    assert isinstance(service.provider, GeminiProvider)
    assert service.provider.model == DEFAULT_GEMINI_MODEL


def test_openai_compatible_provider_remains_selectable(monkeypatch):
    monkeypatch.setenv("NODEFLOW_AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("NODEFLOW_AI_API_KEY", "test-key")

    service = AISuggestionService()

    assert isinstance(service.provider, OpenAICompatibleProvider)


def test_saved_ai_settings_configure_default_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("NODEFLOW_USER_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NODEFLOW_AI_PROVIDER", raising=False)
    monkeypatch.delenv("NODEFLOW_AI_API_KEY", raising=False)
    monkeypatch.delenv("NODEFLOW_AI_MODEL", raising=False)
    monkeypatch.delenv("NODEFLOW_GEMINI_API_URL", raising=False)
    app_paths.get_user_data_dir.cache_clear()
    try:
        settings_service.save(
            {
                "ai_provider": "gemini",
                "ai_api_key": "saved-key",
                "ai_model": "saved-model",
                "ai_api_url": "https://example.test/models/{model}:generateContent",
            }
        )

        service = AISuggestionService()

        assert isinstance(service.provider, GeminiProvider)
        assert service.provider.api_key == "saved-key"
        assert service.provider.model == "saved-model"
        assert service.provider.api_url == (
            "https://example.test/models/saved-model:generateContent"
        )

        monkeypatch.setenv("NODEFLOW_AI_API_KEY", "environment-key")
        assert AISuggestionService().provider.api_key == "environment-key"
    finally:
        app_paths.get_user_data_dir.cache_clear()


def test_service_does_not_persist_suggestions():
    initialize_database()
    project_id = database.add_project("AI Suggestions")
    before = database.get_nodes_for_project(project_id)
    response = {
        "suggestions": [
            {"name": "Temporary", "reason": "Review me", "existing_node_id": 7}
        ]
    }

    suggestions = _service(response).suggest("selected text", NODE_CONTEXT)

    assert suggestions
    assert database.get_nodes_for_project(project_id) == before
