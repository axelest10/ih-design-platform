import pytest

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from designs.services.renderer import render_preview
from designs.services.safe_zone import SOCIAL_SAFE_ZONE_POLICIES


def _design():
    brief = DesignBrief.objects.create(
        title="Safe zone",
        format=DesignBrief.Format.SQUARE,
        product_slug="general-english",
        audience="Audiencia de prueba",
        objective="Validar legibilidad",
    )
    return Design.objects.create(brief=brief, status=Design.Status.SELF_REVIEW)


@pytest.mark.django_db
@pytest.mark.parametrize("template_key", ["square-v1", "story-v1", "portrait-v1"])
def test_each_social_design_version_gets_safe_zone_and_legibility_result(template_key):
    design = _design()
    rendered = render_preview(
        {
            "template_key": template_key,
            "headline": "Título legible",
            "body": "Una experiencia segura.",
            "cta": "Conoce más",
        }
    )
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key=rendered.template_key,
        render_data={**rendered.data, "html": rendered.html, "svg": rendered.svg},
        asset_refs=rendered.asset_refs,
        validation_summary=rendered.validation_summary,
    )

    version.refresh_from_db()
    result = version.validation_summary["safe_zone_check"]
    assert result["status"] == "passed"
    assert result["format"] in SOCIAL_SAFE_ZONE_POLICIES
    assert result["geometry"]["source"] == "renderer.safe_area"
    assert result["contrast"]["status"] == "passed"
    assert version.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING


@pytest.mark.django_db
def test_safe_zone_persists_needs_changes_without_mutating_claude_review_state():
    design = _design()
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"headline": "Título", "body": "Cuerpo"},
        asset_refs=[],
        validation_summary={
            "status": "passed",
            "checks": [
                {
                    "name": "contrast",
                    "status": "needs_changes",
                    "pairs": [{"name": "text_on_surface", "ratio": 2.0}],
                }
            ],
        },
    )

    version.refresh_from_db()
    result = version.validation_summary["safe_zone_check"]
    assert result["status"] == "needs_changes"
    assert version.validation_summary["status"] == "needs_changes"
    assert version.claude_review_status == DesignVersion.ClaudeReviewStatus.PENDING
    assert design.status == Design.Status.SELF_REVIEW


@pytest.mark.django_db
def test_non_social_design_version_is_recorded_as_skipped():
    design = _design()
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="brochure-a4-v1",
        render_data={"pdf_path": "generated/example.pdf"},
        asset_refs=[],
        validation_summary={"status": "passed", "checks": []},
    )

    version.refresh_from_db()
    assert version.validation_summary["safe_zone_check"] == {
        "status": "skipped",
        "reason": "format_without_social_safe_zone_policy",
        "template_key": "brochure-a4-v1",
    }
