from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignReviewComment, DesignVersion

REPO_ROOT = Path(__file__).resolve().parents[1]


def _design_with_version(*, product_slug="general-english"):
    brief = DesignBrief.objects.create(
        title="Diseño para revisión",
        format=DesignBrief.Format.SQUARE,
        product_slug=product_slug,
        audience="Audiencia de prueba",
        objective="Probar el flujo de comentarios",
    )
    design = Design.objects.create(brief=brief, status=Design.Status.SELF_REVIEW)
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"headline": "Título", "body": "Cuerpo", "svg": "<svg></svg>"},
        asset_refs=[],
        validation_summary={"status": "passed"},
    )
    return design, version


def _role_client(role):
    user = get_user_model().objects.create_user(
        username=f"{role}@ihmexico.com",
        email=f"{role}@ihmexico.com",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_reviewer_can_comment_and_read_thread_during_design_test_mode(settings):
    settings.DESIGN_TEST_MODE = True
    design, version = _design_with_version()
    client, reviewer = _role_client("reviewer")
    url = f"/api/v1/designs/{design.pk}/comments/"

    created = client.post(
        url,
        {"version": version.pk, "comment": "Aumentar contraste del CTA."},
        format="json",
    )
    thread = client.get(url)

    assert created.status_code == 201
    assert created.json()["author"] == reviewer.pk
    assert created.json()["author_email"] == reviewer.email
    assert created.json()["version"] == version.pk
    assert thread.status_code == 200
    assert [item["comment"] for item in thread.json()] == ["Aumentar contraste del CTA."]
    assert design.status == Design.Status.SELF_REVIEW


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_designer_cannot_read_or_create_review_comments():
    design, version = _design_with_version()
    client, _ = _role_client("designer")
    url = f"/api/v1/designs/{design.pk}/comments/"

    assert client.get(url).status_code == 403
    assert client.post(
        url,
        {"version": version.pk, "comment": "Comentario no autorizado"},
        format="json",
    ).status_code == 403


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_review_decision_persists_optional_comment_when_test_mode_is_off(settings):
    settings.DESIGN_TEST_MODE = False
    design, version = _design_with_version()
    client, reviewer = _role_client("reviewer")

    response = client.post(
        f"/api/v1/designs/{design.pk}/review/",
        {
            "decision": "approve",
            "version": version.number,
            "comment": "Aprobado para publicación.",
        },
        format="json",
    )

    assert response.status_code == 200
    design.refresh_from_db()
    assert design.status == Design.Status.APPROVED
    comment = DesignReviewComment.objects.get(design=design)
    assert comment.author == reviewer
    assert comment.version == version
    assert comment.comment == "Aprobado para publicación."


@pytest.mark.django_db
def test_product_design_rejects_formal_review_during_first_50_tests(settings):
    settings.DESIGN_TEST_MODE = True
    design, version = _design_with_version(product_slug="ielts-preparation")

    response = APIClient().post(
        f"/api/v1/designs/{design.pk}/review/",
        {"decision": "approve", "version": version.number},
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["next"] == "claude-review"


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_reviewer_profile_exposes_review_and_test_mode_capabilities(settings):
    settings.DESIGN_TEST_MODE = True
    settings.DESIGN_TEST_LIMIT = 50
    client, _ = _role_client("reviewer")

    response = client.get("/api/v1/me/")

    assert response.status_code == 200
    assert response.json()["can_review"] is True
    assert response.json()["design_test_mode"] is True
    assert response.json()["design_test_limit"] == 50


def test_review_page_is_registered():
    response = APIClient().get("/review.html")

    assert response.status_code == 200
    assert b"scripts/review.js" in response.content


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_authenticated_user_exports_an_exact_persisted_svg_version():
    design, first_version = _design_with_version()
    first_version.render_data = {
        **first_version.render_data,
        "svg": '<svg aria-label="Versión uno"></svg>',
    }
    first_version.save(update_fields=["render_data"])
    DesignVersion.objects.create(
        design=design,
        number=2,
        template_key="square-v1",
        render_data={"svg": '<svg aria-label="Versión dos"></svg>'},
    )
    client, _ = _role_client("viewer")

    response = client.get(
        f"/api/v1/designs/{design.pk}/versions/1/export/?output=svg"
    )

    assert response.status_code == 200, response.json()
    assert response.content == b'<svg aria-label="Versi\xc3\xb3n uno"></svg>'
    assert response["Content-Type"] == "image/svg+xml; charset=utf-8"
    assert f'design-{design.pk}-version-1.svg' in response["Content-Disposition"]
    assert "no-store" in response["Cache-Control"]
    assert design.versions.count() == 2


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_version_export_rejects_missing_artifact_and_unknown_format():
    design, _ = _design_with_version()
    client, _ = _role_client("viewer")
    url = f"/api/v1/designs/{design.pk}/versions/1/export/"

    missing = client.get(f"{url}?output=pdf")
    unsupported = client.get(f"{url}?output=png")
    unknown_version = client.get(
        f"/api/v1/designs/{design.pk}/versions/99/export/?output=svg"
    )

    assert missing.status_code == 404
    assert unsupported.status_code == 400
    assert unknown_version.status_code == 404


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_version_export_requires_authenticated_corporate_access():
    design, _ = _design_with_version()

    response = APIClient().get(
        f"/api/v1/designs/{design.pk}/versions/1/export/?output=svg"
    )

    assert response.status_code == 403


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_stored_document_export_streams_persisted_file(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    design, version = _design_with_version(product_slug="")
    path = default_storage.save(
        f"generated-designs/{design.pk}/version-1.pdf",
        ContentFile(b"%PDF-1.4 persisted test"),
    )
    version.render_data = {"pdf_path": path}
    version.save(update_fields=["render_data"])
    client, _ = _role_client("viewer")

    response = client.get(
        f"/api/v1/designs/{design.pk}/versions/1/export/?output=pdf"
    )

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"%PDF-1.4 persisted test"
    assert response["Content-Type"] == "application/pdf"
    assert "no-store" in response["Cache-Control"]


def test_review_ui_exposes_version_history_and_downloads():
    script = (REPO_ROOT / "frontend" / "scripts" / "review.js").read_text(encoding="utf-8")

    assert "Historial de versiones" in script
    assert "Descargar SVG" in script
    assert "Descargar PNG" in script
    assert "Descargar HTML" in script
    assert '"test_ready", "revision_requested"' in script
    assert 'data.get("version_id")' in script
    assert 'data.get("version_number")' in script
