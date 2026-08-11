import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from ai.providers import GenerationResponse
from briefs.models import DesignBrief
from designs.models import Design, DesignVersion


def _brief(**overrides):
    values = {
        "title": "Título original del brief",
        "format": DesignBrief.Format.SQUARE,
        "product_slug": "general-english",
        "audience": "Personas adultas",
        "objective": "Generar solicitudes",
        "generated_prompt": "Copy confirmado por la persona.",
        "prompt_source": DesignBrief.PromptSource.AI_EDITED,
        "status": DesignBrief.Status.READY,
        "language": "es",
        "channel": "instagram",
        "brief_data": {"cta": "register"},
    }
    values.update(overrides)
    return DesignBrief.objects.create(**values)


def _generation_response(content):
    return GenerationResponse(
        provider="openai",
        model="test-model",
        content=content,
    )


@pytest.mark.django_db
def test_confirm_design_creates_first_version_from_ai_json(settings):
    settings.DESIGN_TEST_MODE = True
    brief = _brief()
    structured = {
        "headline": "Inglés que impulsa",
        "body": "Desarrolla habilidades para avanzar profesionalmente.",
        "cta": "Regístrate",
        "eyebrow": "Hello Live English",
    }

    with patch(
        "briefs.services.design_confirmation.OpenAIProvider.generate",
        return_value=_generation_response(json.dumps(structured)),
    ) as generate:
        response = APIClient().post(
            f"/api/v1/briefs/{brief.pk}/confirm-design/",
            {"prompt_override": "Copy final confirmado para la pieza."},
            format="json",
        )

    assert response.status_code == 201, response.json()
    design = Design.objects.get(brief=brief)
    version = DesignVersion.objects.get(design=design, number=1)
    brief.refresh_from_db()
    assert design.status == Design.Status.SELF_REVIEW
    assert design.test_number == 1
    assert brief.status == DesignBrief.Status.IN_REVIEW
    assert version.render_data["headline"] == structured["headline"]
    assert version.render_data["headline"] != brief.title
    assert version.render_data["body"] == structured["body"]
    assert version.render_data["cta"] == structured["cta"]
    assert version.render_data["eyebrow"] == structured["eyebrow"]
    assert response.json()["id"] == design.pk
    assert response.json()["versions"][0]["render_data"]["headline"] == structured["headline"]
    generation_request = generate.call_args.args[0]
    assert generation_request.output_format == "json"
    assert generation_request.authorized_context == {
        "confirmed_prompt": "Copy final confirmado para la pieza.",
        "product_slug": "general-english",
        "channel": "instagram",
        "language": "es",
        "cta_type": "register",
    }


@pytest.mark.django_db
def test_confirm_design_retries_once_after_invalid_json():
    brief = _brief(product_slug="")
    valid = json.dumps(
        {
            "headline": "Aprende hoy",
            "body": "Una experiencia internacional.",
            "cta": "Conoce más",
            "eyebrow": "International House",
        }
    )

    with patch(
        "briefs.services.design_confirmation.OpenAIProvider.generate",
        side_effect=[_generation_response("no es json"), _generation_response(valid)],
    ) as generate:
        response = APIClient().post(f"/api/v1/briefs/{brief.pk}/confirm-design/")

    assert response.status_code == 201, response.json()
    assert generate.call_count == 2
    assert Design.objects.filter(brief=brief).exists()


@pytest.mark.django_db
def test_confirm_design_returns_400_after_two_invalid_ai_responses():
    brief = _brief()

    with patch(
        "briefs.services.design_confirmation.OpenAIProvider.generate",
        side_effect=[
            _generation_response("texto libre"),
            _generation_response('{"headline": "Falta body"}'),
        ],
    ) as generate:
        response = APIClient().post(f"/api/v1/briefs/{brief.pk}/confirm-design/")

    assert response.status_code == 400
    assert generate.call_count == 2
    assert not Design.objects.filter(brief=brief).exists()
    brief.refresh_from_db()
    assert brief.status == DesignBrief.Status.READY


@pytest.mark.django_db
def test_confirm_design_adapts_long_headline_without_truncating_it():
    brief = _brief()
    headline = "Spanish + Culture 20% de descuento"
    structured = {
        "headline": headline,
        "body": "Vive una experiencia completa.",
        "cta": "Conoce más",
        "eyebrow": "Spanish Courses",
    }

    with patch(
        "briefs.services.design_confirmation.OpenAIProvider.generate",
        return_value=_generation_response(json.dumps(structured)),
    ):
        response = APIClient().post(f"/api/v1/briefs/{brief.pk}/confirm-design/")

    assert response.status_code == 201, response.json()
    version = DesignVersion.objects.get(design__brief=brief)
    render_data = version.render_data
    assert render_data["headline"] == headline
    assert render_data["headline_font_size"] < 72
    assert len(render_data["headline_lines"]) >= 2
    assert headline in render_data["html"]
    assert headline in render_data["svg"]
    assert "<tspan" in render_data["svg"]
    assert "{{ headline_svg_markup }}" not in render_data["svg"]


@pytest.mark.django_db
def test_confirm_design_rejects_format_without_template_before_calling_ai():
    brief = _brief(format=DesignBrief.Format.REEL)

    with patch(
        "briefs.services.design_confirmation.OpenAIProvider.generate"
    ) as generate:
        response = APIClient().post(f"/api/v1/briefs/{brief.pk}/confirm-design/")

    assert response.status_code == 400
    assert "no tiene una plantilla" in response.json()["detail"]
    generate.assert_not_called()
    assert not Design.objects.filter(brief=brief).exists()
