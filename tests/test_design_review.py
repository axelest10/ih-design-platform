import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignReviewComment, DesignVersion


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
