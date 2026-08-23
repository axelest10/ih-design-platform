import json
from io import BytesIO
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import pytest

from ai.providers import AIProviderError, GenerationRequest
from ai.providers.gemini_provider import GEMINI_API_BASE_URL, GeminiProvider


def _synthetic_request():
    return GenerationRequest(
        instruction="Resume este contenido público de prueba.",
        authorized_context={"source": "public", "topic": "synthetic-example"},
        output_format="json",
    )


def test_gemini_provider_builds_rest_request_and_parses_response_without_network():
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "responseId": "gemini-synthetic-response",
            "modelVersion": "gemini-evaluation-model-001",
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": '{"summary":"Prueba sintética"}'}]},
                }
            ],
            "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 4},
        }

    provider = GeminiProvider(
        api_key="synthetic-test-key",
        model="gemini-evaluation-model",
        timeout=13,
        transport=transport,
    )
    response = provider.generate(_synthetic_request())

    assert captured["url"] == (
        f"{GEMINI_API_BASE_URL}/models/gemini-evaluation-model:generateContent"
    )
    assert captured["headers"] == {
        "content-type": "application/json",
        "x-goog-api-key": "synthetic-test-key",
    }
    assert captured["timeout"] == 13
    assert json.loads(captured["payload"]["contents"][0]["parts"][0]["text"]) == {
        "instruction": "Resume este contenido público de prueba.",
        "authorized_context": {"source": "public", "topic": "synthetic-example"},
        "output_format": "json",
    }
    assert "datos sintéticos o públicos" in (
        captured["payload"]["systemInstruction"]["parts"][0]["text"]
    )
    assert response.provider == "gemini"
    assert response.model == "gemini-evaluation-model"
    assert response.content == '{"summary":"Prueba sintética"}'
    assert response.metadata == {
        "response_id": "gemini-synthetic-response",
        "model_version": "gemini-evaluation-model-001",
        "finish_reason": "STOP",
        "usage_metadata": {"promptTokenCount": 9, "candidatesTokenCount": 4},
    }


@pytest.mark.parametrize(
    ("api_key", "model"),
    [("", "gemini-evaluation-model"), ("synthetic-test-key", "")],
)
def test_gemini_provider_requires_explicit_key_and_model_without_calling_transport(
    api_key, model
):
    transport = Mock()
    provider = GeminiProvider(api_key=api_key, model=model, transport=transport)

    with pytest.raises(AIProviderError, match="GEMINI_API_KEY y GEMINI_MODEL"):
        provider.generate(_synthetic_request())

    transport.assert_not_called()


def test_gemini_provider_propagates_quota_error_legibly_without_retry():
    error_body = BytesIO(
        json.dumps(
            {
                "error": {
                    "code": 429,
                    "status": "RESOURCE_EXHAUSTED",
                    "message": "Quota exceeded for synthetic test.",
                }
            }
        ).encode("utf-8")
    )
    http_error = HTTPError(
        url="https://generativelanguage.googleapis.com/synthetic",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=error_body,
    )
    provider = GeminiProvider(
        api_key="synthetic-test-key",
        model="gemini-evaluation-model",
    )

    with (
        patch("ai.providers.gemini_provider.urlopen", side_effect=http_error) as urlopen,
        pytest.raises(
            AIProviderError,
            match="HTTP 429.*RESOURCE_EXHAUSTED.*Quota exceeded",
        ),
    ):
        provider.generate(_synthetic_request())

    urlopen.assert_called_once()
