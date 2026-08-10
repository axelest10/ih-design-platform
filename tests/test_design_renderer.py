import pytest
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from designs.services.renderer import RenderValidationError, render_preview


def test_square_v1_renderer_returns_html_and_svg_with_escaped_content():
    rendered = render_preview(
        {
            "headline": "Aprende <inglés>",
            "body": "Una experiencia & segura.",
            "cta": "Conoce más",
        }
    )

    assert rendered.template_key == "square-v1"
    assert rendered.template_version == "1.0.0"
    assert rendered.validation_summary["status"] == "passed"
    assert "&lt;inglés&gt;" in rendered.html
    assert "Una experiencia &amp; segura." in rendered.svg
    assert "data:image/png;base64," in rendered.svg


def test_renderer_rejects_unapproved_logo():
    with pytest.raises(RenderValidationError, match="no está aprobado"):
        render_preview(
            {
                "headline": "Título",
                "body": "Cuerpo",
                "logo_name": "logo-inexistente",
            }
        )


def test_renderer_reports_safe_area_text_layout_and_contrast():
    rendered = render_preview(
        {
            "headline": "Título legible",
            "body": "Una experiencia segura.",
            "cta": "Conoce más",
        }
    )

    checks = {check["name"]: check for check in rendered.validation_summary["checks"]}
    assert checks["safe_area"]["safe_margin_px"] == 72
    assert checks["text_layout"]["status"] == "passed"
    assert checks["contrast"]["pairs"][0]["ratio"] >= 4.5


def test_renderer_rejects_text_that_overflows_safe_width():
    with pytest.raises(RenderValidationError, match="desborda el ancho seguro"):
        render_preview(
            {
                "headline": "A" * 170,
                "body": "Cuerpo",
            }
        )


def test_renderer_rejects_insufficient_contrast():
    with pytest.raises(RenderValidationError, match="contraste"):
        render_preview(
            {
                "headline": "Título",
                "body": "Cuerpo",
                "accent_token": "white",
                "text_token": "white",
            }
        )


@pytest.mark.parametrize(
    ("template_key", "width", "height"),
    [("story-v1", 1080, 1920), ("portrait-v1", 1080, 1350)],
)
def test_renderer_supports_story_and_portrait_templates(template_key, width, height):
    rendered = render_preview(
        {
            "template_key": template_key,
            "headline": "Título legible",
            "body": "Una experiencia segura.",
        }
    )

    assert rendered.template_key == template_key
    assert f'width="{width}"' in rendered.svg
    assert f'height="{height}"' in rendered.svg
    safe_area = next(
        check for check in rendered.validation_summary["checks"] if check["name"] == "safe_area"
    )
    assert safe_area["canvas"] == {"width": width, "height": height}


@pytest.mark.django_db
def test_preview_versions_design_and_moves_it_to_review():
    brief = DesignBrief.objects.create(
        title="Brief de preview",
        format=DesignBrief.Format.SQUARE,
        audience="Audiencia piloto",
        objective="Previsualizar una pieza",
    )
    design = Design.objects.create(brief=brief)

    response = APIClient().post(
        f"/api/v1/designs/{design.pk}/preview/",
        {
            "headline": "Aprende inglés",
            "body": "Una experiencia para tu siguiente paso.",
            "eyebrow": "Cursos de inglés",
            "cta": "Conoce más",
            "logo_name": "ih-mexico-classic-png",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "in_review"
    assert payload["version"] == 1
    assert payload["validation"]["status"] == "passed"
    assert payload["preview"]["html"].startswith("<!doctype html>")
    assert payload["preview"]["svg"].startswith("<svg")
    assert design.versions.count() == 1
    version = DesignVersion.objects.get(design=design)
    assert version.render_data["html"].startswith("<!doctype html>")
    assert version.render_data["svg"].startswith("<svg")


@pytest.mark.django_db
def test_review_approves_the_selected_version():
    brief = DesignBrief.objects.create(
        title="Brief de aprobación",
        format=DesignBrief.Format.SQUARE,
        audience="Audiencia piloto",
        objective="Aprobar una pieza",
    )
    design = Design.objects.create(brief=brief)
    APIClient().post(
        f"/api/v1/designs/{design.pk}/preview/",
        {"headline": "Título", "body": "Cuerpo"},
        format="json",
    )

    response = APIClient().post(
        f"/api/v1/designs/{design.pk}/review/",
        {"decision": "approve", "version": 1},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    design.refresh_from_db()
    assert design.approved_version.number == 1
