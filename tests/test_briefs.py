import pytest
from rest_framework.test import APIClient

from briefs.models import DesignBrief


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
