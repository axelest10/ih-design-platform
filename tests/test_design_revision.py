import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from ai.providers import GenerationResponse
from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from designs.services.renderer import render_preview


def _generation_response(content):
    return GenerationResponse(provider="openai", model="test-model", content=content)


def _design_with_version(**brief_overrides):
    values = {
        "title": "Brief para ajustes",
        "format": DesignBrief.Format.SQUARE,
        "product_slug": "general-english",
        "channel": "instagram",
        "language": "es",
    }
    values.update(brief_overrides)
    brief = DesignBrief.objects.create(**values)
    design = Design.objects.create(brief=brief)
    rendered = render_preview(
        {
            "template_key": "square-v1",
            "headline": "Inglés para avanzar",
            "body": "Aprende con acompañamiento experto.",
            "cta": "Conoce más",
            "eyebrow": "International House",
            "product_slug": brief.product_slug,
            "_allow_validation_warnings": True,
        }
    )
    DesignVersion.objects.create(
        design=design,
        number=1,
        template_key=rendered.template_key,
        render_data={**rendered.data, "html": rendered.html, "svg": rendered.svg},
        asset_refs=rendered.asset_refs,
        validation_summary=rendered.validation_summary,
    )
    return design


@pytest.mark.django_db
def test_revise_creates_next_version_and_recalculates_test_status(settings):
    settings.DESIGN_TEST_MODE = True
    design = _design_with_version()
    updated = {
        "headline": "Avanza en inglés",
        "body": "Aprende con docentes expertos.",
        "cta": "Regístrate",
        "eyebrow": "Hello Live English",
    }

    with patch(
        "designs.services.revision.OpenAIProvider.generate",
        return_value=_generation_response(json.dumps(updated)),
    ) as generate:
        response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Hazlo más directo."},
            format="json",
        )

    assert response.status_code == 201, response.json()
    design.refresh_from_db()
    assert design.status == Design.Status.SELF_REVIEW
    assert design.test_number == 1
    assert design.versions.count() == 2
    version = design.versions.first()
    assert version.number == 2
    assert version.render_data["headline"] == updated["headline"]
    assert version.render_data["body"] == updated["body"]
    assert response.json()["versions"][0]["number"] == 2
    request = generate.call_args.args[0]
    assert request.output_format == "json"
    assert request.authorized_context["instruction"] == "Hazlo más directo."
    assert request.authorized_context["product_slug"] == "general-english"


@pytest.mark.django_db
def test_revise_retries_once_after_invalid_json():
    design = _design_with_version(product_slug="")
    valid = json.dumps(
        {
            "headline": "Aprende hoy",
            "body": "Una experiencia internacional.",
            "cta": "Conoce más",
            "eyebrow": "International House",
        }
    )

    with patch(
        "designs.services.revision.OpenAIProvider.generate",
        side_effect=[_generation_response("no es json"), _generation_response(valid)],
    ) as generate:
        response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Hazlo más cálido."},
            format="json",
        )

    assert response.status_code == 201, response.json()
    assert generate.call_count == 2
    assert design.versions.count() == 2
    design.refresh_from_db()
    assert design.status == Design.Status.IN_REVIEW


@pytest.mark.django_db
def test_revise_returns_400_after_two_invalid_responses_without_new_version():
    design = _design_with_version()

    with patch(
        "designs.services.revision.OpenAIProvider.generate",
        side_effect=[
            _generation_response("texto libre"),
            _generation_response('{"headline": "Falta body"}'),
        ],
    ) as generate:
        response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Cambia el tono."},
            format="json",
        )

    assert response.status_code == 400
    assert generate.call_count == 2
    assert design.versions.count() == 1


@pytest.mark.django_db
def test_two_revisions_chain_from_latest_copy_without_instruction_history():
    design = _design_with_version()
    first = {
        "headline": "Inglés práctico",
        "body": "Aprende para situaciones reales.",
        "cta": "Conoce más",
        "eyebrow": "International House",
    }
    second = {
        "headline": "Inglés para ti",
        "body": "Aprende para tu día a día.",
        "cta": "Regístrate",
        "eyebrow": "International House",
    }

    with patch(
        "designs.services.revision.OpenAIProvider.generate",
        side_effect=[
            _generation_response(json.dumps(first)),
            _generation_response(json.dumps(second)),
        ],
    ) as generate:
        first_response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Hazlo más práctico."},
            format="json",
        )
        second_response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Ahora cambia solo el CTA."},
            format="json",
        )

    assert first_response.status_code == 201, first_response.json()
    assert second_response.status_code == 201, second_response.json()
    assert [version.number for version in design.versions.all()] == [3, 2, 1]
    second_context = generate.call_args_list[1].args[0].authorized_context
    assert second_context["current_headline"] == first["headline"]
    assert second_context["current_body"] == first["body"]
    assert second_context["current_cta"] == first["cta"]
    assert second_context["instruction"] == "Ahora cambia solo el CTA."
    assert "instruction_history" not in second_context


@pytest.mark.django_db
def test_revise_requires_non_empty_instruction_without_creating_version():
    design = _design_with_version()

    with patch("designs.services.revision.OpenAIProvider.generate") as generate:
        response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "   "},
            format="json",
        )

    assert response.status_code == 400
    assert design.versions.count() == 1
    generate.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("brief_format", "template_key"),
    [
        (DesignBrief.Format.SQUARE, "square-v1"),
        (DesignBrief.Format.STORY, "story-v1"),
        (DesignBrief.Format.PORTRAIT, "portrait-v1"),
    ],
)
def test_revise_preserves_previous_version_for_every_social_format(
    brief_format, template_key
):
    brief = DesignBrief.objects.create(
        title=f"Prueba de revisión {template_key}",
        format=brief_format,
        product_slug="general-english",
        channel="instagram",
        language="es",
    )
    design = Design.objects.create(brief=brief)
    rendered = render_preview(
        {
            "template_key": template_key,
            "headline": "Inglés para avanzar",
            "body": "Aprende con acompañamiento experto.",
            "cta": "Conoce más",
            "additional_logo_keys": ["hello-live-kids-svg"],
            "product_slug": brief.product_slug,
            "_allow_validation_warnings": True,
        }
    )
    original = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key=template_key,
        render_data={**rendered.data, "html": rendered.html, "svg": rendered.svg},
        asset_refs=rendered.asset_refs,
        validation_summary=rendered.validation_summary,
    )
    updated = {
        "headline": "Avanza con confianza",
        "body": "Practica inglés para situaciones reales.",
        "cta": "Regístrate",
        "eyebrow": "International House",
    }

    with patch(
        "designs.services.revision.OpenAIProvider.generate",
        return_value=_generation_response(json.dumps(updated)),
    ):
        response = APIClient().post(
            f"/api/v1/designs/{design.pk}/revise/",
            {"instruction": "Haz el mensaje más directo."},
            format="json",
        )

    assert response.status_code == 201, response.json()
    assert [version.number for version in design.versions.all()] == [2, 1]
    original.refresh_from_db()
    assert original.render_data["headline"] == "Inglés para avanzar"
    latest = design.versions.first()
    assert latest.template_key == template_key
    assert latest.render_data["headline"] == updated["headline"]
    assert latest.render_data["additional_logo_keys"] == ["hello-live-kids-svg"]
    assert latest.asset_refs == ["ih-mexico-classic-png", "hello-live-kids-svg"]
