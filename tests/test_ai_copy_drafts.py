import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from rest_framework.test import APIClient

from ai.models import AICallAudit
from ai.providers import AIProviderError, GenerationResponse
from ai.providers.groq_provider import GROQ_BASE_URL
from campaigns.models import Campaign
from catalog.models import Branch, Product
from materials.models import MaterialType
from materials.services.ai_copy_drafts import COPY_DRAFT_INSTRUCTION


def _campaign():
    product = Product.objects.create(code="spanish-courses", name="Spanish Courses")
    return Campaign.objects.create(
        code="confirmed-copy-campaign",
        name="Campaña confirmada",
        product=product,
        starts_on=date.today() - timedelta(days=1),
        ends_on=date.today() + timedelta(days=30),
        approved_copy="Una ruta de aprendizaje confirmada.",
        offer_data={
            "source_status": "confirmed",
            "source_url": "https://example.com/confirmed",
            "benefit": "Evaluación de nivel incluida",
            "cta": "Agenda ahora",
        },
        is_active=True,
    )


def _bundle(slug, **kwargs):
    material_type = MaterialType.objects.get(slug=slug)
    payload = {
        "material_type": material_type,
        "name": f"Borrador {slug}",
        "country": "MX",
        "product_slugs": ["spanish-courses"],
        "brief_context": {"brand_logo_key": "ih-mexico-classic-png"},
    }
    payload.update(kwargs)
    from materials.models import MaterialBundle

    return MaterialBundle.objects.create(**payload)


def _groq_client_factory(content):
    response = SimpleNamespace(
        id="groq-copy-response",
        model="served-groq-model",
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            model_dump=lambda: {"prompt_tokens": 20, "completion_tokens": 12}
        ),
    )
    create = Mock(return_value=response)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    return Mock(return_value=client), create


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["sales-kit", "email-kit"])
def test_confirmed_campaign_kits_store_ai_copy_as_pending_approval_draft(slug):
    bundle = _bundle(slug, campaign=_campaign())
    response = GenerationResponse(
        provider="openai", model="test-model", content=json.dumps(
            {"headline": "Aprende inglés", "body": "Una ruta confirmada.", "cta": "Agenda ahora"}
        )
    )

    with patch(
        "materials.services.ai_copy_drafts.OpenAIProvider.generate", return_value=response
    ) as generate:
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    bundle.refresh_from_db()
    draft = bundle.brief_context["ai_copy_draft"]
    assert draft["status"] == "pending_approval"
    assert draft["needs_confirmation"] is True
    assert draft["copy"]["cta"] == "Agenda ahora"
    assert bundle.status == bundle.Status.DRAFT
    audit = AICallAudit.objects.get(material_bundle=bundle)
    assert audit.status == AICallAudit.Status.COMPLETED
    assert audit.response == response.content
    assert audit.request_context == draft["authorized_context"]
    assert audit.response_metadata == {}
    assert audit.quality_report["status"] == "passed"
    generate.assert_called_once()


@pytest.mark.django_db
def test_venue_copy_requires_confirmed_branch_and_leaves_unconfirmed_cta_empty():
    branch = Branch.objects.get(code="mx-condesa")
    bundle = _bundle(
        "venue-kit",
        branch=branch,
        country="MX",
        product_slugs=["spanish-courses"],
    )
    response = GenerationResponse(
        provider="openai", model="test-model", content=json.dumps(
            {"headline": "Inglés General", "body": "Aprende con International House.", "cta": ""}
        )
    )

    with patch("materials.services.ai_copy_drafts.OpenAIProvider.generate", return_value=response):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    assert (
        result.json()["ai_copy_draft"]["authorized_context"]["branch"]["source_status"]
        == "confirmed"
    )
    assert result.json()["ai_copy_draft"]["copy"]["cta"] == ""


@pytest.mark.django_db
def test_ai_copy_rejects_unconfirmed_campaign_before_calling_provider():
    campaign = _campaign()
    campaign.offer_data["source_status"] = "needs_confirmation"
    campaign.save(update_fields=["offer_data"])
    bundle = _bundle("sales-kit", campaign=campaign)

    with patch("materials.services.ai_copy_drafts.OpenAIProvider.generate") as generate:
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 400
    generate.assert_not_called()
    assert not AICallAudit.objects.filter(material_bundle=bundle).exists()


@pytest.mark.django_db
def test_ai_copy_provider_error_is_audited_once_without_saving_a_draft():
    from ai.providers import AIProviderError

    bundle = _bundle("sales-kit", campaign=_campaign())

    with patch(
        "materials.services.ai_copy_drafts.OpenAIProvider.generate",
        side_effect=AIProviderError("Proveedor no disponible"),
    ) as generate:
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 400
    generate.assert_called_once()
    audit = AICallAudit.objects.get(material_bundle=bundle)
    assert audit.status == AICallAudit.Status.ERROR
    assert audit.response == "Proveedor no disponible"
    assert audit.quality_report == {
        "status": "error",
        "flags": [{"type": "provider_error"}],
    }
    bundle.refresh_from_db()
    assert "ai_copy_draft" not in bundle.brief_context


@pytest.mark.django_db
def test_router_enabled_copy_uses_groq_model_and_contract_without_network(settings):
    settings.AI_ROUTER_ENABLED = True
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = False
    settings.GROQ_API_KEY = "synthetic-groq-key"
    settings.GROQ_MODEL = "openai/gpt-oss-120b"
    bundle = _bundle("sales-kit", campaign=_campaign())
    factory, create = _groq_client_factory(
        json.dumps(
            {
                "headline": "Aprende inglés",
                "body": "Una ruta confirmada.",
                "cta": "Agenda ahora",
            }
        )
    )

    with (
        patch("ai.providers.groq_provider.default_client_factory", factory),
        patch("materials.services.ai_copy_drafts.OpenAIProvider.generate") as openai_generate,
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    factory.assert_called_once_with(
        api_key=settings.GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
        max_retries=0,
    )
    assert create.call_args.kwargs["model"] == settings.GROQ_MODEL
    assert result.json()["ai_copy_draft"]["provider"] == "groq"
    assert result.json()["ai_copy_draft"]["model"] == settings.GROQ_MODEL
    openai_generate.assert_not_called()
    audit = AICallAudit.objects.get(material_bundle=bundle)
    assert audit.provider == "groq"
    assert audit.model == settings.GROQ_MODEL
    assert audit.response_metadata == {
        "response_id": "groq-copy-response",
        "actual_model": "served-groq-model",
        "usage": {"prompt_tokens": 20, "completion_tokens": 12},
        "route_id": "existing-copy-draft-groq-v1",
        "task_type": "copy_draft",
        "flow_classification": "existing_certified_flow",
        "selection_reason": (
            "existing_certified_flow, Groq seleccionado explícitamente por Axel para evitar "
            "costo recurrente"
        ),
    }


@pytest.mark.django_db
def test_router_enabled_groq_copy_keeps_anti_invention_validation(settings):
    settings.AI_ROUTER_ENABLED = True
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = False
    settings.GROQ_API_KEY = "synthetic-groq-key"
    settings.GROQ_MODEL = "openai/gpt-oss-120b"
    bundle = _bundle("sales-kit", campaign=_campaign())
    factory, _create = _groq_client_factory(
        json.dumps(
            {
                "headline": "Aprende inglés en 30 días",
                "body": "Una ruta confirmada.",
                "cta": "Agenda ahora",
            }
        )
    )

    with patch("ai.providers.groq_provider.default_client_factory", factory):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 400
    assert "cifras que no están" in result.json()["detail"]
    bundle.refresh_from_db()
    assert "ai_copy_draft" not in bundle.brief_context
    assert AICallAudit.objects.filter(
        material_bundle=bundle,
        provider="groq",
        status=AICallAudit.Status.COMPLETED,
    ).exists()


@pytest.mark.django_db
def test_router_enabled_copy_without_groq_key_fails_without_fallback(settings):
    settings.AI_ROUTER_ENABLED = True
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = False
    settings.GROQ_API_KEY = ""
    settings.GROQ_MODEL = "openai/gpt-oss-120b"
    bundle = _bundle("sales-kit", campaign=_campaign())
    factory = Mock()

    with (
        patch("ai.providers.groq_provider.default_client_factory", factory),
        patch("materials.services.ai_copy_drafts.OpenAIProvider.generate") as openai_generate,
        patch(
            "ai.providers.openrouter_provider.OpenRouterProvider.generate"
        ) as openrouter_generate,
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 400
    assert "GROQ_API_KEY is not configured" in result.json()["detail"]
    factory.assert_not_called()
    openai_generate.assert_not_called()
    openrouter_generate.assert_not_called()
    audit = AICallAudit.objects.get(material_bundle=bundle)
    assert audit.provider == "groq"
    assert audit.status == AICallAudit.Status.ERROR
    assert audit.response == "GROQ_API_KEY is not configured"
    bundle.refresh_from_db()
    assert "ai_copy_draft" not in bundle.brief_context


@pytest.mark.django_db
def test_prompt_improvement_disabled_preserves_original_copy_request_and_draft(settings):
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = False
    settings.AI_ROUTER_ENABLED = False
    bundle = _bundle("sales-kit", campaign=_campaign())
    response = GenerationResponse(
        provider="openai",
        model="test-model",
        content=json.dumps(
            {"headline": "Aprende inglés", "body": "Una ruta confirmada.", "cta": "Agenda ahora"}
        ),
    )

    with (
        patch(
            "materials.services.ai_copy_drafts.OpenAIProvider.generate",
            autospec=True,
            return_value=response,
        ) as generate,
        patch(
            "ai.providers.groq_provider.GroqProvider.generate",
            autospec=True,
        ) as groq_generate,
        patch("materials.services.ai_copy_drafts.routed_generate") as routed,
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    provider, request = generate.call_args.args
    assert provider.name == "openai"
    assert request.instruction == COPY_DRAFT_INSTRUCTION
    assert request.output_format == "json"
    draft = result.json()["ai_copy_draft"]
    assert set(draft) == {
        "status",
        "source_status",
        "needs_confirmation",
        "provider",
        "model",
        "copy",
        "authorized_context",
    }
    assert AICallAudit.objects.filter(material_bundle=bundle).count() == 1
    groq_generate.assert_not_called()
    routed.assert_not_called()


@pytest.mark.django_db
def test_prompt_improvement_success_reaches_openai_and_is_traced(settings):
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = True
    settings.AI_ROUTER_ENABLED = False
    settings.GROQ_API_KEY = "synthetic-groq-key"
    settings.GROQ_MODEL = "openai/gpt-oss-120b"
    bundle = _bundle("sales-kit", campaign=_campaign())
    improved = GenerationResponse(
        provider="groq",
        model=settings.GROQ_MODEL,
        content="Devuelve un copy claro, breve y fiel al contexto autorizado.",
    )
    final = GenerationResponse(
        provider="openai",
        model="test-openai-model",
        content=json.dumps(
            {"headline": "Aprende inglés", "body": "Una ruta confirmada.", "cta": "Agenda ahora"}
        ),
    )

    with (
        patch(
            "ai.providers.groq_provider.GroqProvider.generate",
            autospec=True,
            return_value=improved,
        ) as groq_generate,
        patch(
            "materials.services.ai_copy_drafts.OpenAIProvider.generate",
            autospec=True,
            return_value=final,
        ) as openai_generate,
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    improvement_request = groq_generate.call_args.args[1]
    final_request = openai_generate.call_args.args[1]
    assert improvement_request.authorized_context == final_request.authorized_context
    assert final_request.instruction.startswith(improved.content)
    assert "No inventes precios, porcentajes, fechas" in final_request.instruction
    draft = result.json()["ai_copy_draft"]
    assert draft["prompt_improvement"] == {
        "attempted": True,
        "used": True,
        "instruction_source": "improved",
        "provider": "groq",
        "model": settings.GROQ_MODEL,
    }
    audits = AICallAudit.objects.filter(material_bundle=bundle).order_by("created_at")
    assert audits.count() == 2
    assert audits[0].provider == "groq"
    assert audits[0].response_metadata["task_type"] == "prompt_improvement"
    assert audits[1].provider == "openai"


@pytest.mark.django_db
def test_prompt_improvement_keeps_final_anti_invention_validation(settings):
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = True
    settings.GROQ_API_KEY = "synthetic-groq-key"
    bundle = _bundle("sales-kit", campaign=_campaign())
    improved = GenerationResponse(
        provider="groq",
        model="openai/gpt-oss-120b",
        content="Escribe un copy claro usando solo el contexto autorizado.",
    )
    unsafe_final = GenerationResponse(
        provider="openai",
        model="test-openai-model",
        content=json.dumps(
            {
                "headline": "Aprende en 30 días",
                "body": "Una ruta confirmada.",
                "cta": "Agenda ahora",
            }
        ),
    )

    with (
        patch(
            "ai.providers.groq_provider.GroqProvider.generate",
            autospec=True,
            return_value=improved,
        ),
        patch(
            "materials.services.ai_copy_drafts.OpenAIProvider.generate",
            autospec=True,
            return_value=unsafe_final,
        ),
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 400
    assert "cifras que no están" in result.json()["detail"]
    bundle.refresh_from_db()
    assert "ai_copy_draft" not in bundle.brief_context


@pytest.mark.django_db
def test_prompt_improvement_provider_failure_falls_back_to_original_instruction(settings):
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = True
    settings.AI_ROUTER_ENABLED = False
    settings.GROQ_API_KEY = "synthetic-groq-key"
    bundle = _bundle("sales-kit", campaign=_campaign())
    final = GenerationResponse(
        provider="openai",
        model="test-openai-model",
        content=json.dumps(
            {"headline": "Aprende inglés", "body": "Una ruta confirmada.", "cta": "Agenda ahora"}
        ),
    )

    with (
        patch(
            "ai.providers.groq_provider.GroqProvider.generate",
            autospec=True,
            side_effect=AIProviderError("Groq no configurado"),
        ),
        patch(
            "materials.services.ai_copy_drafts.OpenAIProvider.generate",
            autospec=True,
            return_value=final,
        ) as openai_generate,
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    assert openai_generate.call_args.args[1].instruction == COPY_DRAFT_INSTRUCTION
    trace = result.json()["ai_copy_draft"]["prompt_improvement"]
    assert trace == {
        "attempted": True,
        "used": False,
        "instruction_source": "original",
        "fallback_reason": "provider_error",
    }
    audits = AICallAudit.objects.filter(material_bundle=bundle)
    assert audits.filter(provider="groq", status=AICallAudit.Status.ERROR).exists()
    assert audits.filter(provider="openai", status=AICallAudit.Status.COMPLETED).exists()


@pytest.mark.django_db
def test_prompt_improvement_empty_response_falls_back_without_breaking_copy(settings):
    settings.AI_PROMPT_IMPROVEMENT_ENABLED = True
    settings.GROQ_API_KEY = "synthetic-groq-key"
    bundle = _bundle("sales-kit", campaign=_campaign())
    empty = GenerationResponse(
        provider="groq",
        model="openai/gpt-oss-120b",
        content="   ",
    )
    final = GenerationResponse(
        provider="openai",
        model="test-openai-model",
        content=json.dumps(
            {"headline": "Aprende inglés", "body": "Una ruta confirmada.", "cta": "Agenda ahora"}
        ),
    )

    with (
        patch(
            "ai.providers.groq_provider.GroqProvider.generate",
            autospec=True,
            return_value=empty,
        ),
        patch(
            "materials.services.ai_copy_drafts.OpenAIProvider.generate",
            autospec=True,
            return_value=final,
        ) as openai_generate,
    ):
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    assert openai_generate.call_args.args[1].instruction == COPY_DRAFT_INSTRUCTION
    trace = result.json()["ai_copy_draft"]["prompt_improvement"]
    assert trace["used"] is False
    assert trace["fallback_reason"] == "invalid_response"
