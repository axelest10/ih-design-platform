import base64
import hashlib
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import pytest
from django.conf import settings as django_settings
from PIL import Image

from ai.providers import (
    AIProviderError,
    AnthropicVisualReviewProvider,
    CloudflareWorkersAIProvider,
    GenerationRequest,
    GroqProvider,
    OpenRouterProvider,
)
from ai.providers.cloudflare_provider import CLOUDFLARE_API_BASE_URL
from ai.providers.cloudflare_provider import _default_transport as cloudflare_transport
from ai.providers.groq_provider import GROQ_BASE_URL
from ai.providers.openrouter_provider import OPENROUTER_BASE_URL
from ai.services.routing import (
    DEFAULT_AI_PROVIDER_REGISTRY,
    TASK_POLICIES,
    AIProviderCapability,
    AIProviderProductionStatus,
    AITaskType,
    ai_router_enabled,
    select_provider,
)


def _request(**context):
    return GenerationRequest(
        instruction="Crea una salida sintética de prueba.",
        authorized_context={"source": "synthetic", **context},
        output_format="json",
    )


def test_free_tier_credentials_remain_empty_and_models_use_safe_defaults():
    assert django_settings.GROQ_API_KEY == ""
    assert django_settings.GROQ_MODEL == "openai/gpt-oss-120b"
    assert django_settings.OPENROUTER_API_KEY == ""
    assert django_settings.OPENROUTER_MODEL == ""
    assert django_settings.CLOUDFLARE_ACCOUNT_ID == ""
    assert django_settings.CLOUDFLARE_API_TOKEN == ""
    assert (
        django_settings.CLOUDFLARE_IMAGE_MODEL
        == "@cf/black-forest-labs/flux-2-klein-4b"
    )


def _openai_compatible_client(*, content="Salida sintética"):
    response = SimpleNamespace(
        id="synthetic-response-id",
        model="served-model-version",
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            model_dump=lambda: {"prompt_tokens": 12, "completion_tokens": 5}
        ),
    )
    create = Mock(return_value=response)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    factory = Mock(return_value=client)
    return factory, create


class SyntheticRateLimitError(Exception):
    status_code = 429

    def __init__(self, retry_after):
        super().__init__("Synthetic rate limit")
        self.response = SimpleNamespace(
            status_code=429,
            headers={"retry-after": retry_after},
        )


def test_groq_provider_builds_openai_compatible_request_and_response_without_network():
    factory, create = _openai_compatible_client()
    provider = GroqProvider(api_key="synthetic-groq-key", client_factory=factory)

    response = provider.generate(_request(topic="public-example"))

    factory.assert_called_once_with(
        api_key="synthetic-groq-key",
        base_url=GROQ_BASE_URL,
        max_retries=0,
    )
    call = create.call_args.kwargs
    assert call["model"] == "openai/gpt-oss-120b"
    assert json.loads(call["messages"][1]["content"]) == {
        "instruction": "Crea una salida sintética de prueba.",
        "authorized_context": {"source": "synthetic", "topic": "public-example"},
        "output_format": "json",
    }
    assert response.provider == "groq"
    assert response.model == "openai/gpt-oss-120b"
    assert response.content == "Salida sintética"
    assert response.metadata["response_id"] == "synthetic-response-id"


def test_groq_provider_rejects_missing_credentials_without_calling_client():
    factory = Mock()
    provider = GroqProvider(api_key="", client_factory=factory)

    with pytest.raises(AIProviderError, match="GROQ_API_KEY"):
        provider.generate(_request())

    factory.assert_not_called()


def test_groq_provider_propagates_retry_after_without_automatic_retry():
    factory, create = _openai_compatible_client()
    create.side_effect = SyntheticRateLimitError("9")
    provider = GroqProvider(api_key="synthetic-groq-key", client_factory=factory)

    with pytest.raises(AIProviderError, match="HTTP 429; retry-after=9"):
        provider.generate(_request())

    create.assert_called_once()
    assert factory.call_args.kwargs["max_retries"] == 0


def test_openrouter_provider_builds_fixed_model_request_and_response_without_network():
    factory, create = _openai_compatible_client(content="OpenRouter sintético")
    provider = OpenRouterProvider(
        api_key="synthetic-openrouter-key",
        model="openai/gpt-oss-120b:free",
        client_factory=factory,
    )

    response = provider.generate(_request())

    factory.assert_called_once_with(
        api_key="synthetic-openrouter-key",
        base_url=OPENROUTER_BASE_URL,
        max_retries=0,
    )
    assert create.call_args.kwargs["model"] == "openai/gpt-oss-120b:free"
    assert response.provider == "openrouter"
    assert response.model == "openai/gpt-oss-120b:free"
    assert response.content == "OpenRouter sintético"


@pytest.mark.parametrize(
    ("api_key", "model"),
    [("", "openai/gpt-oss-120b:free"), ("synthetic-openrouter-key", "")],
)
def test_openrouter_provider_requires_explicit_credentials_and_model(api_key, model):
    factory = Mock()
    provider = OpenRouterProvider(
        api_key=api_key,
        model=model,
        client_factory=factory,
    )

    with pytest.raises(AIProviderError, match="OPENROUTER_API_KEY y OPENROUTER_MODEL"):
        provider.generate(_request())

    factory.assert_not_called()


def test_openrouter_provider_rejects_random_free_router_without_calling_client():
    factory = Mock()
    provider = OpenRouterProvider(
        api_key="synthetic-openrouter-key",
        model="openrouter/free",
        client_factory=factory,
    )

    with pytest.raises(AIProviderError, match="openrouter/free no está permitido"):
        provider.generate(_request())

    factory.assert_not_called()


def test_openrouter_provider_propagates_retry_after_without_automatic_retry():
    factory, create = _openai_compatible_client()
    create.side_effect = SyntheticRateLimitError("12")
    provider = OpenRouterProvider(
        api_key="synthetic-openrouter-key",
        model="openai/gpt-oss-120b:free",
        client_factory=factory,
    )

    with pytest.raises(AIProviderError, match="HTTP 429; retry-after=12"):
        provider.generate(_request())

    create.assert_called_once()
    assert factory.call_args.kwargs["max_retries"] == 0


def _png_bytes(width=4, height=3):
    output = BytesIO()
    Image.new("RGB", (width, height), "#009EE2").save(output, format="PNG")
    return output.getvalue()


def test_cloudflare_provider_stores_image_and_returns_descriptor_without_network():
    image_bytes = _png_bytes()
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "result": {"image": base64.b64encode(image_bytes).decode("ascii")},
            "result_info": {"request_id": "cloudflare-synthetic-request"},
        }

    artifact_store = Mock(return_value="ai-generated/cloudflare/synthetic.png")
    provider = CloudflareWorkersAIProvider(
        account_id="synthetic-account",
        api_token="synthetic-token",
        timeout=14,
        transport=transport,
        artifact_store=artifact_store,
    )

    response = provider.generate(_request(width=1024, height=1024))

    assert captured["url"] == (
        f"{CLOUDFLARE_API_BASE_URL}/accounts/synthetic-account/ai/run/"
        "@cf/black-forest-labs/flux-2-klein-4b"
    )
    assert captured["headers"] == {
        "authorization": "Bearer synthetic-token",
    }
    assert captured["payload"]["width"] == 1024
    assert captured["payload"]["height"] == 1024
    assert "sin logos ni copy final" in captured["payload"]["prompt"]
    assert captured["timeout"] == 14
    checksum = hashlib.sha256(image_bytes).hexdigest()
    artifact_store.assert_called_once_with(image_bytes, "image/png", checksum)
    descriptor = json.loads(response.content)
    assert descriptor == {
        "artifact_ref": "ai-generated/cloudflare/synthetic.png",
        "mime_type": "image/png",
        "width": 4,
        "height": 3,
        "checksum": checksum,
    }
    assert response.provider == "cloudflare-workers-ai"
    assert response.model == "@cf/black-forest-labs/flux-2-klein-4b"


def test_cloudflare_default_transport_serializes_required_multipart_without_network():
    class SyntheticResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"result":"synthetic-base64"}'

    with patch(
        "ai.providers.cloudflare_provider.urlopen",
        return_value=SyntheticResponse(),
    ) as urlopen:
        result = cloudflare_transport(
            "https://api.cloudflare.com/synthetic",
            {"authorization": "Bearer synthetic-token"},
            {"prompt": "Synthetic prompt", "width": 1024, "height": 1024},
            10,
        )

    request = urlopen.call_args.args[0]
    assert request.get_header("Content-type").startswith("multipart/form-data; boundary=")
    assert b'name="prompt"\r\n\r\nSynthetic prompt' in request.data
    assert b'name="width"\r\n\r\n1024' in request.data
    assert b'name="height"\r\n\r\n1024' in request.data
    assert result == {"result": "synthetic-base64"}


@pytest.mark.parametrize(
    ("account_id", "api_token"),
    [("", "synthetic-token"), ("synthetic-account", "")],
)
def test_cloudflare_provider_requires_both_credentials_without_network(
    account_id, api_token
):
    transport = Mock()
    artifact_store = Mock()
    provider = CloudflareWorkersAIProvider(
        account_id=account_id,
        api_token=api_token,
        transport=transport,
        artifact_store=artifact_store,
    )

    with pytest.raises(AIProviderError, match="CLOUDFLARE_ACCOUNT_ID.*CLOUDFLARE_API_TOKEN"):
        provider.generate(_request())

    transport.assert_not_called()
    artifact_store.assert_not_called()


def test_cloudflare_provider_propagates_3036_rate_limit_without_retry():
    error_body = BytesIO(
        json.dumps(
            {
                "success": False,
                "errors": [
                    {
                        "code": 3036,
                        "message": "Daily free Neurons allocation exhausted.",
                    }
                ],
            }
        ).encode("utf-8")
    )
    http_error = HTTPError(
        url="https://api.cloudflare.com/synthetic",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=error_body,
    )
    provider = CloudflareWorkersAIProvider(
        account_id="synthetic-account",
        api_token="synthetic-token",
        artifact_store=Mock(),
    )

    with (
        patch("ai.providers.cloudflare_provider.urlopen", side_effect=http_error) as urlopen,
        pytest.raises(AIProviderError, match="HTTP 429.*3036.*Neurons allocation exhausted"),
    ):
        provider.generate(_request())

    urlopen.assert_called_once()


def test_free_tier_registrations_are_production_candidates_with_only_groq_opt_in_task():
    expected = {
        "groq_generation": AIProviderCapability.GENERATE,
        "openrouter_generation": AIProviderCapability.GENERATE,
        "cloudflare_image_generation": AIProviderCapability.IMAGE_GENERATION,
    }
    for key, capability in expected.items():
        registration = DEFAULT_AI_PROVIDER_REGISTRY.get(key)
        assert registration.capability == capability
        assert registration.production_status == AIProviderProductionStatus.PRODUCTION
    prompt_policy = TASK_POLICIES[AITaskType.PROMPT_IMPROVEMENT]
    assert prompt_policy.provider_key == "groq_generation"
    assert {"openrouter_generation", "cloudflare_image_generation"}.isdisjoint(
        policy.provider_key for policy in TASK_POLICIES.values()
    )


@pytest.mark.parametrize("router_enabled", [False, True])
def test_free_tier_routes_keep_explicit_groq_copy_and_anthropic_review(settings, router_enabled):
    settings.AI_ROUTER_ENABLED = router_enabled
    settings.GROQ_API_KEY = "synthetic-groq-key"
    settings.GROQ_MODEL = "openai/gpt-oss-120b"
    settings.ANTHROPIC_API_KEY = "synthetic-anthropic-key"
    settings.ANTHROPIC_MODEL = "certified-anthropic-model"

    copy_selection = select_provider(AITaskType.COPY_DRAFT)
    review_selection = select_provider(AITaskType.AUTOMATIC_VISUAL_REVIEW)

    assert ai_router_enabled() is router_enabled
    assert set(TASK_POLICIES) == {
        AITaskType.COPY_DRAFT,
        AITaskType.AUTOMATIC_VISUAL_REVIEW,
        AITaskType.PROMPT_IMPROVEMENT,
    }
    assert copy_selection.registration.key == "groq_generation"
    assert isinstance(copy_selection.provider, GroqProvider)
    assert review_selection.registration.key == "anthropic_visual_review"
    assert isinstance(review_selection.provider, AnthropicVisualReviewProvider)
