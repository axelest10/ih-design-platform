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
    assert DesignBrief.objects.get().format == "square"


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
