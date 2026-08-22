import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from ai.models import AICallAudit
from ai.providers import GenerationResponse
from campaigns.models import Campaign
from catalog.models import Branch, Product
from materials.models import MaterialType


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
def test_router_enabled_copy_uses_current_openai_provider_model_and_contract(settings):
    settings.AI_ROUTER_ENABLED = True
    settings.OPENAI_API_KEY = "router-test-key"
    settings.OPENAI_MODEL = "router-test-openai-model"
    bundle = _bundle("sales-kit", campaign=_campaign())
    response = GenerationResponse(
        provider="openai",
        model=settings.OPENAI_MODEL,
        content=json.dumps(
            {"headline": "Aprende inglés", "body": "Una ruta confirmada.", "cta": "Agenda ahora"}
        ),
        metadata={"response_id": "same-openai-response"},
    )

    with patch(
        "ai.providers.openai_provider.OpenAIProvider.generate",
        autospec=True,
        return_value=response,
    ) as generate:
        result = APIClient().post(f"/api/v1/material-bundles/{bundle.pk}/suggest-copy/")

    assert result.status_code == 201, result.json()
    provider, request = generate.call_args.args
    assert provider.name == "openai"
    assert provider.api_key == settings.OPENAI_API_KEY
    assert provider.model == settings.OPENAI_MODEL
    assert request.output_format == "json"
    assert result.json()["ai_copy_draft"]["provider"] == "openai"
    assert result.json()["ai_copy_draft"]["model"] == settings.OPENAI_MODEL
    audit = AICallAudit.objects.get(material_bundle=bundle)
    assert audit.provider == "openai"
    assert audit.model == settings.OPENAI_MODEL
    assert audit.response == response.content
    assert audit.response_metadata == {
        "response_id": "same-openai-response",
        "route_id": "existing-copy-draft-openai-v1",
        "task_type": "copy_draft",
        "flow_classification": "existing_certified_flow",
        "selection_reason": "existing_certified_flow, único candidato",
    }
