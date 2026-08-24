import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from ai.providers import GenerationResponse
from briefs.models import DesignBrief
from designs.models import Design, DesignDelivery
from security.models import TransactionalEmailDelivery


def _user(role, email):
    user = get_user_model().objects.create_user(username=email, email=email)
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    return user


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_brief_review_delivery_flow_records_requester_recipient_and_link(
    settings, monkeypatch
):
    settings.DESIGN_TEST_MODE = True
    settings.DESIGN_TEST_ALLOW_HUMAN_APPROVAL = True
    settings.EMAIL_DELIVERY_MODE = "allowlist"
    settings.POSTMARK_MESSAGE_STREAM = "outbound"
    requester = _user("designer", "requester@ihmexico.com")
    settings.EMAIL_ALLOWED_RECIPIENTS = (requester.email,)
    reviewer = _user("reviewer", "reviewer@ihmexico.com")
    creator_client = APIClient()
    creator_client.force_authenticate(user=requester)

    brief_response = creator_client.post(
        "/api/v1/briefs/",
        {
            "title": "Curso de inglés para avanzar",
            "format": "square",
            "product_slug": "general-english",
            "audience": "Personas adultas",
            "objective": "Generar solicitudes",
            "brief_data": {"cta": "register"},
        },
        format="json",
    )
    assert brief_response.status_code == 201, brief_response.json()
    brief_id = brief_response.json()["id"]

    structured = {
        "headline": "Inglés para avanzar",
        "body": "Desarrolla habilidades para tus próximos retos.",
        "cta": "Regístrate",
        "eyebrow": "International House",
    }
    monkeypatch.setattr(
        "briefs.services.design_confirmation.OpenAIProvider.generate",
        lambda _provider, _request: GenerationResponse(
            provider="openai", model="test-model", content=json.dumps(structured)
        ),
    )
    generated = creator_client.post(
        f"/api/v1/briefs/{brief_id}/confirm-design/",
        {"prompt_override": "Copy confirmado por la persona."},
        format="json",
    )
    assert generated.status_code == 201, generated.json()
    design_id = generated.json()["id"]

    sent = {}

    def fake_send_transactional_email(**kwargs):
        sent.update(kwargs)
        return "postmark-message-123"

    monkeypatch.setattr(
        "designs.tasks.send_transactional_email", fake_send_transactional_email
    )
    reviewer_client = APIClient()
    reviewer_client.force_authenticate(user=reviewer)
    approved = reviewer_client.post(
        f"/api/v1/designs/{design_id}/review/",
        {"decision": "approve", "version": 1},
        format="json",
    )

    assert approved.status_code == 200, approved.json()
    delivery = DesignDelivery.objects.get(design_id=design_id, version__number=1)
    assert delivery.requested_by_id == requester.pk
    assert delivery.recipient_email == requester.email
    assert delivery.status == DesignDelivery.Status.DELIVERED
    assert delivery.provider_message_id == "postmark-message-123"
    assert f"/api/v1/designs/{design_id}/versions/1/export/?output=svg" in delivery.download_url
    assert sent["to"] == requester.email
    assert sent["tag"] == "approved-design"
    assert delivery.download_url in sent["text_body"]
    email_delivery = TransactionalEmailDelivery.objects.get(
        provider_message_id="postmark-message-123"
    )
    assert email_delivery.recipient == requester.email
    assert email_delivery.status == TransactionalEmailDelivery.Status.ACCEPTED
    assert sent["metadata"] == {
        "email_delivery_id": str(email_delivery.pk),
        "design_delivery_id": str(delivery.pk),
    }

    design = Design.objects.get(pk=design_id)
    assert design.approved_version.number == 1
    assert approved.json()["delivery"]["status"] == DesignDelivery.Status.DELIVERED


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_human_approval_remains_blocked_without_staging_escape_hatch(settings):
    settings.DESIGN_TEST_MODE = True
    settings.DESIGN_TEST_ALLOW_HUMAN_APPROVAL = False
    brief = DesignBrief.objects.create(
        title="Prueba de protección",
        format=DesignBrief.Format.SQUARE,
        product_slug="general-english",
        audience="Personas adultas",
        objective="Probar protección",
    )
    design = Design.objects.create(brief=brief, status=Design.Status.SELF_REVIEW)
    from designs.models import DesignVersion

    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"svg": "<svg></svg>"},
        validation_summary={"status": "passed"},
    )
    reviewer = _user("reviewer", "protected-reviewer@ihmexico.com")
    client = APIClient()
    client.force_authenticate(user=reviewer)

    response = client.post(
        f"/api/v1/designs/{design.pk}/review/",
        {"decision": "approve", "version": version.number},
        format="json",
    )

    assert response.status_code == 409
    assert "DESIGN_TEST_ALLOW_HUMAN_APPROVAL=1" in response.json()["detail"]
    assert not DesignDelivery.objects.filter(design=design).exists()
