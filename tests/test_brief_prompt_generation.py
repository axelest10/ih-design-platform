import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from ai.providers import AIProviderError
from briefs.models import DesignBrief


def _brief():
    return DesignBrief.objects.create(
        title="Inglés para crecer",
        format=DesignBrief.Format.SQUARE,
        audience="Profesionales jóvenes",
        objective="Generar solicitudes de información",
        requested_message="Impulsa tu carrera con inglés",
        brief_data={
            "audience_need": "Mejorar sus oportunidades laborales",
            "campaign_info": "Campaña de posicionamiento",
            "required_information": "Modalidad en línea",
            "cta": "Solicita información",
            "cta_destination": "Formulario web",
            "tone": "Cercano y profesional",
            "visual_elements": "Personas colaborando",
            "ignored_field": "No debe enviarse",
        },
        language="es",
        channel="instagram",
    )


@pytest.mark.django_db
def test_generate_prompt_saves_ai_copy_and_marks_brief_ready(settings):
    settings.GROQ_API_KEY = "test-key"
    settings.GROQ_MODEL = "openai/gpt-oss-120b"
    brief = _brief()
    provider_response = SimpleNamespace(
        id="synthetic-groq-response",
        model="openai/gpt-oss-120b",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        "  Mejora tu inglés y abre nuevas oportunidades profesionales.  "
                    )
                )
            )
        ],
        usage=None,
    )
    create = Mock(return_value=provider_response)
    client_factory = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
    )

    with patch(
        "ai.providers.groq_provider.default_client_factory",
        client_factory,
    ):
        response = APIClient().post(f"/api/v1/briefs/{brief.pk}/generate-prompt/")

    assert response.status_code == 200, response.json()
    brief.refresh_from_db()
    assert brief.generated_prompt == "Mejora tu inglés y abre nuevas oportunidades profesionales."
    assert brief.prompt_source == DesignBrief.PromptSource.AI
    assert brief.status == DesignBrief.Status.READY
    assert response.json()["generated_prompt"] == brief.generated_prompt
    assert response.json()["prompt_source"] == "ai"
    client_factory.assert_called_once_with(
        api_key="test-key",
        base_url="https://api.groq.com/openai/v1",
        max_retries=0,
    )
    transport_payload = json.loads(create.call_args.kwargs["messages"][1]["content"])
    assert create.call_args.kwargs["model"] == "openai/gpt-oss-120b"
    assert transport_payload["output_format"] == "text"
    assert transport_payload["authorized_context"] == {
        "title": "Inglés para crecer",
        "audience": "Profesionales jóvenes",
        "objective": "Generar solicitudes de información",
        "requested_message": "Impulsa tu carrera con inglés",
        "brief_data": {
            "audience_need": "Mejorar sus oportunidades laborales",
            "campaign_info": "Campaña de posicionamiento",
            "required_information": "Modalidad en línea",
            "cta": "Solicita información",
            "cta_destination": "Formulario web",
            "tone": "Cercano y profesional",
            "visual_elements": "Personas colaborando",
        },
        "language": "es",
        "channel": "instagram",
    }
    assert "no uses JSON" in transport_payload["instruction"]
    assert "no inventes precios" in transport_payload["instruction"]


@pytest.mark.django_db
def test_generate_prompt_falls_back_to_manual_without_changing_draft_status(settings):
    settings.GROQ_API_KEY = ""
    settings.GROQ_MODEL = ""
    brief = _brief()

    with patch(
        "briefs.services.prompt_generation.GroqProvider.generate",
        side_effect=AIProviderError("GROQ_API_KEY is not configured"),
    ):
        response = APIClient().post(f"/api/v1/briefs/{brief.pk}/generate-prompt/")

    assert response.status_code == 200, response.json()
    brief.refresh_from_db()
    assert brief.generated_prompt == ""
    assert brief.prompt_source == DesignBrief.PromptSource.MANUAL
    assert brief.status == DesignBrief.Status.DRAFT
    assert response.json()["generated_prompt"] == ""
    assert response.json()["prompt_source"] == "manual"
    assert response.json()["status"] == "draft"


@pytest.mark.corporate_auth
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("platform_admin", 200),
        ("marketing", 200),
        ("designer", 200),
        ("reviewer", 403),
        ("viewer", 403),
    ],
)
def test_generate_prompt_uses_brief_write_roles(role, expected_status):
    user = get_user_model().objects.create_user(
        username=f"prompt-{role}",
        email=f"prompt-{role}@ihmexico.com",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    brief = _brief()
    brief.created_by = user
    brief.save(update_fields=["created_by"])
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "briefs.services.prompt_generation.GroqProvider.generate",
        side_effect=AIProviderError("provider unavailable"),
    ):
        response = client.post(f"/api/v1/briefs/{brief.pk}/generate-prompt/")

    assert response.status_code == expected_status
