import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from ai.providers import GenerationResponse
from ai.providers.anthropic_review import (
    ANTHROPIC_MESSAGES_URL,
    REQUIRED_REVIEW_CHECKS,
    AnthropicVisualReviewProvider,
)
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
    checks = [
        {
            "name": name,
            "status": "needs_changes" if name == failing_check else "pass",
            "finding": "Hallazgo sintético de prueba.",
        }
        for name in REQUIRED_REVIEW_CHECKS
    ]
    return {"decision": decision, "summary": "Revisión sintética.", "checks": checks}


def _request():
    return VisualReviewRequest(
        version_id=7,
        design_id=3,
        template_key="square-v1",
        render_data={
            "headline": "Inglés para avanzar",
            "body": "Contenido visible",
            "cta": "Conoce más",
            "logo_name": "ih-mexico-drive-svg",
            "additional_logo_keys": ["hello-live-kids-svg"],
            "svg": '<svg><image href="data:image/png;base64,QUJD" /></svg>',
        },
        asset_refs=["ih-mexico-drive-svg", "hello-live-kids-svg"],
        validation_summary={"status": "passed"},
    )


def test_anthropic_provider_uses_messages_structured_output_and_sanitized_svg():
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "id": "msg_test_123",
            "content": [{"type": "text", "text": json.dumps(_report())}],
        }

    provider = AnthropicVisualReviewProvider(
        api_key="test-secret",
        model="test-model",
        timeout=12,
        transport=transport,
    )
    result = provider.review(_request())

    assert result.decision == "pass"
    assert result.report["integration_status"] == "active"
    assert result.report["response_id"] == "msg_test_123"
    assert captured["url"] == ANTHROPIC_MESSAGES_URL
    assert captured["headers"]["x-api-key"] == "test-secret"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["timeout"] == 12
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["output_config"]["format"]["type"] == "json_schema"
    prompt = captured["payload"]["messages"][0]["content"][-1]["text"]
    assert "embedded-logo://omitted" in prompt
    assert "data:image/png;base64,QUJD" not in prompt
    assert "test-secret" not in json.dumps(captured["payload"])


def test_anthropic_provider_rejects_missing_or_inconsistent_checks():
    invalid = _report(decision="pass", failing_check="contrast")
    provider = AnthropicVisualReviewProvider(
        api_key="test-secret",
        model="test-model",
        transport=lambda *_args: {
            "id": "msg_invalid",
            "content": [{"type": "text", "text": json.dumps(invalid)}],
        },
    )

    with pytest.raises(VisualReviewProviderError, match="contradice"):
        provider.review(_request())


def test_configured_provider_falls_back_without_key_or_model(settings):
    settings.ANTHROPIC_API_KEY = ""
    settings.ANTHROPIC_MODEL = ""

    assert isinstance(configured_visual_review_provider(), NeedsConfirmationClaudeReviewProvider)


@pytest.mark.django_db
def test_provider_failure_keeps_generated_version_and_records_pending_error():
    brief = DesignBrief.objects.create(
        title="Prueba de error Anthropic",
        format=DesignBrief.Format.SQUARE,
        audience="Audiencia sintética",
        objective="Conservar la versión",
    )
    design = Design.objects.create(brief=brief)
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"headline": "Prueba", "svg": "<svg></svg>"},
    )

    class FailingProvider:
        name = "anthropic-test"

        def review(self, request):
            raise VisualReviewProviderError("Falla operativa sintética.")

    run_automatic_design_review(version, provider=FailingProvider())

    assert DesignVersion.objects.filter(pk=version.pk).exists()
    version.refresh_from_db()
    assert version.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
    assert version.claude_review["integration_status"] == "provider_error"
    assert version.claude_review["provider"] == "anthropic-test"


@pytest.mark.django_db
def test_initial_generation_and_revision_each_trigger_review_for_latest_version():
    brief = DesignBrief.objects.create(
        title="Flujo automático Anthropic",
        format=DesignBrief.Format.SQUARE,
        product_slug="general-english",
        audience="Audiencia sintética",
        objective="Validar revisión automática",
        generated_prompt="Copy confirmado.",
        status=DesignBrief.Status.READY,
        language="es",
        channel="instagram",
    )
    first_copy = {
        "headline": "Inglés para avanzar",
        "body": "Aprende con acompañamiento experto.",
        "cta": "Conoce más",
        "eyebrow": "International House",
    }
    second_copy = {
        "headline": "Avanza con confianza",
        "body": "Practica inglés para situaciones reales.",
        "cta": "Regístrate",
        "eyebrow": "International House",
    }

    class PassingProvider:
        name = "anthropic-test"

        def __init__(self):
            self.version_ids = []

        def review(self, request):
            self.version_ids.append(request.version_id)
            return VisualReviewResult(decision="pass", report=_report())

    provider = PassingProvider()
    responses = [
        GenerationResponse("openai", "test", json.dumps(first_copy)),
        GenerationResponse("openai", "test", json.dumps(second_copy)),
    ]
    with (
        patch(
            "ai.services.design_review.configured_visual_review_provider",
            return_value=provider,
        ),
        patch(
            "briefs.services.design_confirmation.OpenAIProvider.generate",
            return_value=responses[0],
        ),
    ):
        initial = APIClient().post(f"/api/v1/briefs/{brief.pk}/confirm-design/")

    design = Design.objects.get(brief=brief)
    with (
        patch(
            "ai.services.design_review.configured_visual_review_provider",
            return_value=provider,
        ),
        patch("designs.services.revision.OpenAIProvider.generate", return_value=responses[1]),
    ):
        revised = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Hazlo más directo."},
            format="json",
        )

    assert initial.status_code == 201, initial.json()
    assert revised.status_code == 201, revised.json()
    assert len(provider.version_ids) == 2
    assert [version.number for version in design.versions.all()] == [2, 1]
    assert set(
        design.versions.values_list("claude_review_status", flat=True)
    ) == {DesignVersion.ClaudeReviewStatus.PASS}
    design.refresh_from_db()
    assert design.status == Design.Status.TEST_READY
