import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from ai.models import AICallAudit
from ai.providers.anthropic_review import AnthropicVisualReviewProvider
from ai.providers.cloudflare_vision_review import CloudflareVisionReviewProvider
from ai.providers.visual_review_contract import REQUIRED_REVIEW_CHECKS, REVIEW_SCHEMA
from ai.services import (
    NeedsConfirmationClaudeReviewProvider,
    VisualReviewProviderError,
    VisualReviewRequest,
    VisualReviewResult,
    configured_visual_review_provider,
    run_automatic_design_review,
)
from briefs.models import DesignBrief
from designs.models import Design, DesignVersion


def _report(*, decision="pass", failing_check=None):
    return {
        "decision": decision,
        "summary": "Revisión visual sintética.",
        "checks": [
            {
                "name": name,
                "status": "needs_changes" if name == failing_check else "pass",
                "finding": "Hallazgo sintético.",
            }
            for name in REQUIRED_REVIEW_CHECKS
        ],
    }


def _request():
    return VisualReviewRequest(
        version_id=7,
        design_id=3,
        template_key="square-v1",
        render_data={
            "headline": "Prueba sintética",
            "body": "Sin datos de cliente",
            "cta": "Conoce más",
            "svg": '<svg><image href="data:image/png;base64,QUJD" /></svg>',
            "preview_image_data_uri": "data:image/png;base64,QUJD",
        },
        asset_refs=["synthetic-logo"],
        validation_summary={"status": "passed"},
    )


def _version(title="Revisión visual Cloudflare"):
    brief = DesignBrief.objects.create(
        title=title,
        format=DesignBrief.Format.SQUARE,
        audience="Audiencia sintética",
        objective="Validar revisión visual",
    )
    design = Design.objects.create(brief=brief)
    return DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data=_request().render_data,
        asset_refs=_request().asset_refs,
        validation_summary=_request().validation_summary,
    )


def _configure_cloudflare(settings):
    settings.AI_VISUAL_REVIEW_FREE_TIER_ENABLED = True
    settings.CLOUDFLARE_ACCOUNT_ID = "account-test"
    settings.CLOUDFLARE_API_TOKEN = "token-test"
    settings.CLOUDFLARE_VISION_MODEL = "@cf/meta/llama-3.2-11b-vision-instruct"


def test_cloudflare_vision_builds_structured_multimodal_request_without_network():
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "success": True,
            "result": {"id": "cf-review-123", "response": _report()},
        }

    provider = CloudflareVisionReviewProvider(
        account_id="account/test",
        api_token="secret-test",
        model="@cf/meta/llama-3.2-11b-vision-instruct",
        timeout=13,
        transport=transport,
    )

    result = provider.review(_request())

    assert result.decision == "pass"
    assert result.report["integration_status"] == "active"
    assert result.report["response_id"] == "cf-review-123"
    assert captured["url"].endswith(
        "/accounts/account%2Ftest/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
    )
    assert captured["headers"]["authorization"] == "Bearer secret-test"
    assert captured["timeout"] == 13
    assert captured["payload"]["image"] == "data:image/png;base64,QUJD"
    assert captured["payload"]["response_format"] == {
        "type": "json_schema",
        "json_schema": REVIEW_SCHEMA,
    }
    prompt = captured["payload"]["messages"][1]["content"]
    assert "embedded-logo://omitted" in prompt
    assert "data:image/png;base64,QUJD" not in prompt
    assert "secret-test" not in json.dumps(captured["payload"])


def test_cloudflare_vision_requires_all_configuration_without_calling_transport():
    transport_called = False

    def transport(*_args):
        nonlocal transport_called
        transport_called = True
        return {}

    provider = CloudflareVisionReviewProvider(
        account_id="account-test",
        api_token="",
        model="@cf/meta/llama-3.2-11b-vision-instruct",
        transport=transport,
    )

    with pytest.raises(VisualReviewProviderError, match="CLOUDFLARE_API_TOKEN"):
        provider.review(_request())

    assert transport_called is False


@pytest.mark.django_db
@pytest.mark.parametrize("anthropic_configured", [True, False])
def test_free_tier_flag_off_with_router_enabled_preserves_current_visual_review_behavior(
    settings, anthropic_configured
):
    settings.AI_ROUTER_ENABLED = True
    settings.AI_VISUAL_REVIEW_FREE_TIER_ENABLED = False
    settings.CLOUDFLARE_ACCOUNT_ID = "configured-but-disabled"
    settings.CLOUDFLARE_API_TOKEN = "configured-but-disabled"
    settings.CLOUDFLARE_VISION_MODEL = "configured-but-disabled"
    settings.ANTHROPIC_API_KEY = "anthropic-key" if anthropic_configured else ""
    settings.ANTHROPIC_MODEL = "anthropic-model" if anthropic_configured else ""
    version = _version(f"Router activo Anthropic={anthropic_configured}")

    result = VisualReviewResult(decision="pass", report=_report())
    with patch.object(
        AnthropicVisualReviewProvider,
        "review",
        autospec=True,
        return_value=result,
    ) as anthropic_review:
        reviewed = run_automatic_design_review(version)

    if anthropic_configured:
        assert anthropic_review.call_count == 1
        assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PASS
        assert reviewed.claude_review["provider"] == "anthropic"
    else:
        assert anthropic_review.call_count == 0
        assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
        assert reviewed.claude_review["provider"] == "claude-stub"


@pytest.mark.django_db
@pytest.mark.parametrize("anthropic_configured", [True, False])
def test_free_tier_flag_off_with_router_disabled_preserves_current_visual_review_behavior(
    settings, anthropic_configured
):
    settings.AI_ROUTER_ENABLED = False
    settings.AI_VISUAL_REVIEW_FREE_TIER_ENABLED = False
    settings.CLOUDFLARE_ACCOUNT_ID = "configured-but-disabled"
    settings.CLOUDFLARE_API_TOKEN = "configured-but-disabled"
    settings.CLOUDFLARE_VISION_MODEL = "configured-but-disabled"
    settings.ANTHROPIC_API_KEY = "anthropic-key" if anthropic_configured else ""
    settings.ANTHROPIC_MODEL = "anthropic-model" if anthropic_configured else ""
    version = _version(f"Router inactivo Anthropic={anthropic_configured}")

    result = VisualReviewResult(decision="pass", report=_report())
    with patch.object(
        AnthropicVisualReviewProvider,
        "review",
        autospec=True,
        return_value=result,
    ) as anthropic_review:
        reviewed = run_automatic_design_review(version)

    if anthropic_configured:
        assert anthropic_review.call_count == 1
        assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PASS
        assert reviewed.claude_review["provider"] == "anthropic"
    else:
        assert anthropic_review.call_count == 0
        assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
        assert reviewed.claude_review["provider"] == "claude-stub"


def test_configured_visual_review_prefers_anthropic_when_both_are_configured(settings):
    _configure_cloudflare(settings)
    settings.ANTHROPIC_API_KEY = "anthropic-key"
    settings.ANTHROPIC_MODEL = "anthropic-model"

    provider = configured_visual_review_provider()

    assert isinstance(provider, AnthropicVisualReviewProvider)


def test_configured_visual_review_uses_cloudflare_without_anthropic(settings):
    _configure_cloudflare(settings)
    settings.ANTHROPIC_API_KEY = ""
    settings.ANTHROPIC_MODEL = ""

    provider = configured_visual_review_provider()

    assert isinstance(provider, CloudflareVisionReviewProvider)


@pytest.mark.parametrize(
    "missing_setting",
    ["CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_VISION_MODEL"],
)
def test_incomplete_cloudflare_opt_in_falls_back_to_anthropic(settings, missing_setting):
    _configure_cloudflare(settings)
    setattr(settings, missing_setting, "")
    settings.ANTHROPIC_API_KEY = "anthropic-key"
    settings.ANTHROPIC_MODEL = "anthropic-model"

    provider = configured_visual_review_provider()

    assert isinstance(provider, AnthropicVisualReviewProvider)


def test_configured_visual_review_uses_safe_fallback_without_providers(settings):
    settings.AI_VISUAL_REVIEW_FREE_TIER_ENABLED = False
    settings.CLOUDFLARE_ACCOUNT_ID = ""
    settings.CLOUDFLARE_API_TOKEN = ""
    settings.CLOUDFLARE_VISION_MODEL = ""
    settings.ANTHROPIC_API_KEY = ""
    settings.ANTHROPIC_MODEL = ""

    provider = configured_visual_review_provider()

    assert isinstance(provider, NeedsConfirmationClaudeReviewProvider)


@pytest.mark.django_db
def test_cloudflare_visual_review_validates_shared_schema_and_persists_decision(settings):
    _configure_cloudflare(settings)
    settings.AI_ROUTER_ENABLED = True
    version = _version()

    with patch(
        "ai.providers.cloudflare_vision_review._default_transport",
        return_value={"result": {"response": _report()}},
    ) as transport:
        reviewed = run_automatic_design_review(version)

    reviewed.refresh_from_db()
    reviewed.design.refresh_from_db()
    assert transport.call_count == 1
    assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PASS
    assert reviewed.claude_review["provider"] == "cloudflare-workers-ai-vision"
    assert reviewed.claude_review["model"] == settings.CLOUDFLARE_VISION_MODEL
    assert reviewed.design.status == Design.Status.TEST_READY
    audit = AICallAudit.objects.get(design_version=version)
    assert audit.provider == "cloudflare-workers-ai-vision"
    assert audit.model == settings.CLOUDFLARE_VISION_MODEL
    assert audit.status == AICallAudit.Status.COMPLETED


@pytest.mark.django_db
def test_cloudflare_429_is_recorded_as_safe_pending_provider_error(settings):
    _configure_cloudflare(settings)
    version = _version("Cloudflare 429")
    error_body = BytesIO(
        json.dumps(
            {
                "errors": [
                    {
                        "code": 3036,
                        "message": "You have used up your daily free allocation of 10,000 neurons.",
                    }
                ]
            }
        ).encode()
    )
    http_error = HTTPError(
        "https://api.cloudflare.com/test",
        429,
        "Too Many Requests",
        hdrs=None,
        fp=error_body,
    )
    provider = CloudflareVisionReviewProvider()

    with patch(
        "ai.providers.cloudflare_vision_review.urlopen", side_effect=http_error
    ) as urlopen_mock:
        reviewed = run_automatic_design_review(version, provider=provider)

    expected = (
        "Cloudflare Workers AI agotó el límite o la capacidad disponible con HTTP 429 "
        "(3036: You have used up your daily free allocation of 10,000 neurons.)."
    )
    assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
    assert urlopen_mock.call_count == 1
    assert reviewed.claude_review["integration_status"] == "provider_error"
    assert reviewed.claude_review["summary"] == expected
    audit = AICallAudit.objects.get(design_version=version)
    assert audit.status == AICallAudit.Status.ERROR
    assert json.loads(audit.response) == {"error": expected}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({"result": {"response": "not-json"}}, "devolvió JSON inválido"),
        (
            {"result": {"response": {"decision": "pass", "summary": "Sin checks"}}},
            "fuera del contrato",
        ),
        (
            {"result": {"response": _report(decision="pass", failing_check="contrast")}},
            "contradice sus controles",
        ),
    ],
)
def test_invalid_cloudflare_report_is_recorded_as_safe_pending_provider_error(
    settings, response, message
):
    _configure_cloudflare(settings)
    version = _version(f"Cloudflare inválido {message}")
    provider = CloudflareVisionReviewProvider(transport=lambda *_args: response)

    reviewed = run_automatic_design_review(version, provider=provider)

    assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
    assert reviewed.claude_review["integration_status"] == "provider_error"
    assert message in reviewed.claude_review["summary"]
    audit = AICallAudit.objects.get(design_version=version)
    assert audit.status == AICallAudit.Status.ERROR
    assert audit.response_metadata["raw_provider_response"] == response


@pytest.mark.django_db
def test_invalid_cloudflare_report_preserves_route_and_raw_response_metadata(settings):
    _configure_cloudflare(settings)
    version = _version("Cloudflare inválido con metadata de ruta")
    response = {
        "success": True,
        "result": {
            "id": "cf-invalid-123",
            "response": {"decision": "pass", "summary": "Sin checks"},
        },
    }
    provider = CloudflareVisionReviewProvider(transport=lambda *_args: response)

    reviewed = run_automatic_design_review(version, provider=provider)

    assert reviewed.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
    assert reviewed.claude_review["integration_status"] == "provider_error"
    assert reviewed.claude_review["summary"] == (
        "Cloudflare Workers AI devolvió un reporte fuera del contrato."
    )
    audit = AICallAudit.objects.get(design_version=version)
    assert audit.provider == "cloudflare-workers-ai-vision"
    assert audit.status == AICallAudit.Status.ERROR
    assert audit.response_metadata == {"raw_provider_response": response}


def test_visual_review_free_tier_flag_defaults_off():
    from django.conf import settings

    assert settings.AI_VISUAL_REVIEW_FREE_TIER_ENABLED is False
