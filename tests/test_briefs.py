import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.middleware.csrf import get_token
from django.test import RequestFactory
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion


def _brief_payload(**overrides):
    payload = {
        "title": "Aprende inglés hoy",
        "format": "square",
        "audience": "Personas adultas interesadas en aprender inglés",
        "objective": "Solicitar información",
        "requested_message": "Conoce nuestros cursos",
    }
    payload.update(overrides)
    return payload


def _authenticated_client_with_csrf(role):
    user = get_user_model().objects.create_user(
        username=f"brief-csrf-{role}",
        email=f"brief-csrf-{role}@ihmexico.com",
        password="safe-password-123",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient(enforce_csrf_checks=True)
    assert client.login(username=user.username, password="safe-password-123")
    request = RequestFactory().get("/")
    token = get_token(request)
    client.cookies["csrftoken"] = request.META["CSRF_COOKIE"]
    return client, token


@pytest.mark.django_db
def test_valid_brief_is_created():
    payload = {
        "title": "Brief piloto",
        "format": "square",
        "audience": "Personas adultas interesadas en aprender inglés",
        "objective": "Solicitar información",
        "requested_message": "Conoce nuestros cursos",
        "source_references": ["marketing-ticket-001"],
        "constraints": {"critical_text_in_template": True},
    }

    response = APIClient().post("/api/v1/briefs/", payload, format="json")

    assert response.status_code == 201
    brief = DesignBrief.objects.get()
    assert brief.format == "square"
    assert brief.material_type is None


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_authenticated_user_can_create_brief_with_csrf_header():
    client, token = _authenticated_client_with_csrf("designer")
    payload = {
        "title": "Brief autenticado con CSRF",
        "format": "square",
        "audience": "Personas adultas interesadas en aprender inglés",
        "objective": "Solicitar información",
        "requested_message": "Conoce nuestros cursos",
    }

    rejected = client.post("/api/v1/briefs/", payload, format="json")
    assert rejected.status_code == 403

    response = client.post(
        "/api/v1/briefs/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )

    assert response.status_code == 201, response.json()
    assert DesignBrief.objects.get().created_by.email == "brief-csrf-designer@ihmexico.com"


@pytest.mark.django_db
def test_social_post_material_type_is_optional_and_keeps_format_mapping():
    from materials.models import MaterialType

    social_post = MaterialType.objects.get(slug="social-post")
    response = APIClient().post(
        "/api/v1/briefs/",
        {
            "title": "Post social formalizado",
            "format": "story",
            "material_type": social_post.pk,
            "audience": "Personas adultas interesadas en aprender inglés",
            "objective": "Solicitar información",
            "requested_message": "Conoce nuestros cursos",
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    brief = DesignBrief.objects.get()
    assert brief.format == "story"
    assert brief.material_type_id == social_post.pk


@pytest.mark.django_db
def test_invalid_brief_format_is_rejected():
    response = APIClient().post(
        "/api/v1/briefs/",
        {
            "title": "Brief inválido",
            "format": "unknown",
            "audience": "Audiencia",
            "objective": "Objetivo",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_supported_brief_automatically_creates_rendered_design(settings):
    settings.DESIGN_TEST_MODE = True
    response = APIClient().post(
        "/api/v1/briefs/",
        _brief_payload(product_slug="general-english"),
        format="json",
    )

    assert response.status_code == 201, response.json()
    brief = DesignBrief.objects.get(pk=response.json()["id"])
    design = Design.objects.get(brief=brief)
    version = DesignVersion.objects.get(design=design, number=1)
    assert brief.status == DesignBrief.Status.IN_REVIEW
    assert design.status == Design.Status.SELF_REVIEW
    assert design.test_number == 1
    assert version.template_key == "square-v1"
    assert version.render_data["html"]
    assert version.render_data["svg"]
    assert version.asset_refs
    assert version.validation_summary["status"] in {"passed", "needs_changes"}


@pytest.mark.django_db
def test_unsupported_brief_format_is_saved_ready_without_design():
    response = APIClient().post(
        "/api/v1/briefs/",
        _brief_payload(format="reel"),
        format="json",
    )

    assert response.status_code == 201, response.json()
    brief = DesignBrief.objects.get(pk=response.json()["id"])
    assert brief.status == DesignBrief.Status.READY
    assert not Design.objects.filter(brief=brief).exists()


@pytest.mark.django_db
def test_invalid_render_content_saves_brief_ready_without_500_or_design():
    response = APIClient().post(
        "/api/v1/briefs/",
        _brief_payload(title="W" * 180),
        format="json",
    )

    assert response.status_code == 201, response.json()
    brief = DesignBrief.objects.get(pk=response.json()["id"])
    assert brief.status == DesignBrief.Status.READY
    assert not Design.objects.filter(brief=brief).exists()


@pytest.mark.django_db
def test_brief_cta_type_is_rendered_as_expected_copy():
    response = APIClient().post(
        "/api/v1/briefs/",
        _brief_payload(brief_data={"cta": "buy"}),
        format="json",
    )

    assert response.status_code == 201, response.json()
    version = DesignVersion.objects.get(design__brief_id=response.json()["id"])
    assert version.render_data["cta"] == "Compra ahora"
    assert "Compra ahora" in version.render_data["html"]
    assert "Compra ahora" in version.render_data["svg"]
