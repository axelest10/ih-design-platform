import re

import pytest
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from designs.services.renderer import (
    SVG_BASE_POSITIONS,
    TEMPLATE_SPECS,
    RenderValidationError,
    _fit_text,
    render_preview,
)


def _svg_positions(svg):
    body = re.search(r'<text x="120" y="([^"]+)"[^>]+font-weight="400">', svg)
    cta_rect = re.search(r'<rect x="120" y="([^"]+)" width="300" height="72"', svg)
    cta_text = re.search(r'<text x="270" y="([^"]+)"', svg)
    assert body and cta_rect and cta_text
    return tuple(float(match.group(1)) for match in (body, cta_rect, cta_text))


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
    assert "{{" not in rendered.html
    assert "{{" not in rendered.svg


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


def test_renderer_rejects_logo_region_near_edge_before_safe_zone_persistence(monkeypatch):
    monkeypatch.setitem(
        TEMPLATE_SPECS["square-v1"]["regions"],
        "logo_row",
        (0, 120, 884, 92),
    )

    with pytest.raises(RenderValidationError, match="región 'logo_row' sale de la zona segura"):
        render_preview(
            {
                "headline": "Título legible",
                "body": "Una experiencia segura.",
            }
        )


def test_renderer_adapts_text_that_exceeds_the_base_safe_width():
    headline = "Spanish + Culture 20% de descuento"
    rendered = render_preview({"headline": headline, "body": "Cuerpo"})

    assert rendered.data["headline"] == headline
    assert rendered.data["headline_font_size"] < 72
    assert len(rendered.data["headline_lines"]) >= 2
    assert "<tspan" in rendered.svg


def test_svg_moves_body_by_headline_extra_line_height():
    headline = "Aprende inglés para crecer y abrir nuevas oportunidades profesionales"
    rendered = render_preview({"headline": headline, "body": "Cuerpo corto"})

    line_count = len(rendered.data["headline_lines"])
    assert line_count >= 2
    expected_extra = (line_count - 1) * round(
        rendered.data["headline_font_size"] * 1.15, 2
    )
    body_y, cta_rect_y, cta_text_y = _svg_positions(rendered.svg)
    assert body_y == 580 + expected_extra
    assert body_y > 580
    assert cta_rect_y == 720 + expected_extra
    assert cta_text_y == 766 + expected_extra


def test_svg_moves_cta_for_wrapped_body_without_moving_body_baseline():
    body = (
        "Aprende inglés con acompañamiento experto y actividades prácticas para "
        "comunicarte con confianza todos los días."
    )
    rendered = render_preview({"headline": "Inglés para ti", "body": body})

    assert len(rendered.data["headline_lines"]) == 1
    body_line_count = len(rendered.data["body_lines"])
    assert body_line_count >= 2
    body_extra = (body_line_count - 1) * round(
        rendered.data["body_font_size"] * 1.15, 2
    )
    body_y, cta_rect_y, cta_text_y = _svg_positions(rendered.svg)
    assert body_y == 580
    assert cta_rect_y == 720 + body_extra
    assert cta_text_y == 766 + body_extra


def test_svg_moves_cta_by_combined_headline_and_body_extra_height():
    headline = "Aprende inglés para crecer y abrir nuevas oportunidades profesionales"
    body = (
        "Desarrolla habilidades prácticas para comunicarte con confianza en situaciones "
        "personales, académicas y profesionales."
    )
    rendered = render_preview({"headline": headline, "body": body})

    headline_extra = (len(rendered.data["headline_lines"]) - 1) * round(
        rendered.data["headline_font_size"] * 1.15, 2
    )
    body_extra = (len(rendered.data["body_lines"]) - 1) * round(
        rendered.data["body_font_size"] * 1.15, 2
    )
    assert headline_extra > 0
    assert body_extra > 0
    body_y, cta_rect_y, cta_text_y = _svg_positions(rendered.svg)
    assert body_y == 580 + headline_extra
    assert cta_rect_y == 720 + headline_extra + body_extra
    assert cta_text_y == 766 + headline_extra + body_extra


def test_svg_rejects_copy_that_pushes_cta_beyond_safe_area():
    extreme = ("palabra " * 22).strip()

    with pytest.raises(RenderValidationError, match="demasiado largo para esta plantilla"):
        render_preview({"headline": extreme, "body": extreme})


@pytest.mark.parametrize(
    ("template_key", "body_y", "cta_rect_y", "cta_text_y"),
    [
        ("square-v1", 580, 720, 766),
        ("story-v1", 780, 1040, 1086),
        ("portrait-v1", 620, 860, 906),
    ],
)
def test_svg_keeps_original_positions_for_short_copy(
    template_key, body_y, cta_rect_y, cta_text_y
):
    rendered = render_preview(
        {
            "template_key": template_key,
            "headline": "Inglés para ti",
            "body": "Aprende hoy.",
            "cta": "Conoce más",
        }
    )

    assert _svg_positions(rendered.svg) == (body_y, cta_rect_y, cta_text_y)
    assert "{{ body_y }}" not in rendered.svg
    assert "{{ cta_rect_y }}" not in rendered.svg
    assert "{{ cta_text_y }}" not in rendered.svg


def test_fit_text_keeps_base_size_for_short_text():
    fitted = _fit_text("headline", "Inglés para ti", 72, 820)

    assert fitted["font_size"] == 72
    assert fitted["lines"] == ["Inglés para ti"]
    assert fitted["adjustment"] == "none"


def test_fit_text_reduces_size_before_wrapping():
    value = "A" * 24
    fitted = _fit_text("headline", value, 72, 820)

    assert fitted["font_size"] == 60
    assert fitted["lines"] == [value]
    assert fitted["adjustment"] == "font_size"


def test_fit_text_wraps_by_complete_words_at_minimum_size():
    value = "Aprende inglés para crecer y abrir nuevas oportunidades profesionales"
    fitted = _fit_text("headline", value, 72, 820)

    assert fitted["font_size"] == 44
    assert len(fitted["lines"]) >= 2
    assert " ".join(fitted["lines"]) == value
    assert fitted["adjustment"] == "wrapped"


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
    assert "{{" not in rendered.html
    assert "{{" not in rendered.svg
    safe_area = next(
        check for check in rendered.validation_summary["checks"] if check["name"] == "safe_area"
    )
    assert safe_area["canvas"] == {"width": width, "height": height}


@pytest.mark.parametrize("template_key", ["square-v1", "story-v1", "portrait-v1"])
def test_social_templates_reflow_long_copy_and_preserve_dual_branding(template_key):
    headline = "Aprende inglés para crecer y abrir nuevas oportunidades profesionales"
    body = (
        "Desarrolla habilidades prácticas para comunicarte con confianza en situaciones "
        "personales, académicas y profesionales."
    )
    cta = "Conoce más"
    additional_logo = "hello-live-kids-svg"

    rendered = render_preview(
        {
            "template_key": template_key,
            "headline": headline,
            "body": body,
            "cta": cta,
            "additional_logo_keys": [additional_logo],
        }
    )

    assert len(rendered.data["headline_lines"]) >= 2
    assert len(rendered.data["body_lines"]) >= 2
    assert rendered.asset_refs == ["ih-mexico-classic-png", additional_logo]
    assert rendered.data["additional_logo_keys"] == [additional_logo]
    for visible_copy in (headline, body, cta, "Hello Live Kids"):
        assert visible_copy in rendered.html
        assert visible_copy in rendered.svg

    positions = SVG_BASE_POSITIONS[template_key]
    headline_extra = (len(rendered.data["headline_lines"]) - 1) * round(
        rendered.data["headline_font_size"] * 1.15, 2
    )
    body_extra = (len(rendered.data["body_lines"]) - 1) * round(
        rendered.data["body_font_size"] * 1.15, 2
    )
    body_y, cta_rect_y, cta_text_y = _svg_positions(rendered.svg)
    assert body_y == pytest.approx(positions["body_y"] + headline_extra)
    assert cta_rect_y == pytest.approx(
        positions["cta_rect_y"] + headline_extra + body_extra
    )
    assert cta_text_y == pytest.approx(
        positions["cta_text_y"] + headline_extra + body_extra
    )
    spec = TEMPLATE_SPECS[template_key]
    assert cta_rect_y + positions["cta_rect_height"] <= spec["height"] - spec["safe_margin"]


@pytest.mark.parametrize("template_key", ["square-v1", "story-v1", "portrait-v1"])
def test_social_templates_reject_copy_over_the_global_readability_limit(template_key):
    with pytest.raises(RenderValidationError, match="supera el máximo"):
        render_preview(
            {
                "template_key": template_key,
                "headline": "x" * 181,
                "body": "Cuerpo legible",
            }
        )


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
