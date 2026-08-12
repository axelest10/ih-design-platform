import json
import logging
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from common.observability import operation_event
from designs.models import Design, DesignVersion


def _events(caplog):
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "ih_design.operations"
    ]


def test_correlation_id_is_returned_and_invalid_input_is_not_reflected():
    supplied = str(uuid4())
    accepted = APIClient().get("/api/v1/health/", HTTP_X_REQUEST_ID=supplied)
    generated = APIClient().get(
        "/api/v1/health/",
        HTTP_X_REQUEST_ID="invalid\nrequest-id",
    )

    assert accepted["X-Request-ID"] == supplied
    assert generated["X-Request-ID"] != "invalid\nrequest-id"
    assert str(uuid4()).count("-") == generated["X-Request-ID"].count("-")


def test_operation_logger_drops_sensitive_and_unknown_fields(caplog):
    caplog.set_level(logging.INFO, logger="ih_design.operations")

    operation_event(
        "security.test",
        status="ok",
        user_id=7,
        password="secret-password",
        token="secret-token",
        api_key="secret-api-key",
        cookie="secret-cookie",
        prompt="secret-prompt",
        image="data:image/png;base64,secret-image",
    )

    event = _events(caplog)[-1]
    serialized = json.dumps(event)
    assert event["status"] == "ok"
    assert event["user_id"] == 7
    for secret in (
        "secret-password",
        "secret-token",
        "secret-api-key",
        "secret-cookie",
        "secret-prompt",
        "secret-image",
    ):
        assert secret not in serialized


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_login_events_never_include_submitted_credentials(caplog):
    user = get_user_model().objects.create_user(
        username="observed-user",
        email="observed-user@ihmexico.com",
        password="submitted-password-123",
    )
    caplog.set_level(logging.INFO, logger="ih_design.operations")
    client = APIClient()

    failed = client.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": "wrong-secret-password"},
        format="json",
    )
    success = client.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": "submitted-password-123"},
        format="json",
    )

    assert failed.status_code == 401
    assert success.status_code == 200
    serialized = json.dumps(_events(caplog))
    assert "wrong-secret-password" not in serialized
    assert "submitted-password-123" not in serialized
    assert user.username not in serialized
    assert '"status": "failed"' in serialized
    assert '"status": "success"' in serialized


@pytest.mark.django_db
def test_brief_and_every_design_version_emit_identifier_only_events(caplog):
    caplog.set_level(logging.INFO, logger="ih_design.operations")
    brief = DesignBrief.objects.create(
        title="Sensitive brief title that must not be logged",
        format=DesignBrief.Format.SQUARE,
        audience="Sensitive audience",
        objective="Sensitive objective",
    )
    design = Design.objects.create(brief=brief)
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"svg": "data:image/png;base64,secret-binary"},
    )

    events = _events(caplog)
    version_event = next(item for item in events if item["event"] == "design.version_created")
    assert version_event["design_id"] == design.pk
    assert version_event["version_id"] == version.pk
    assert "Sensitive brief title" not in json.dumps(events)
    assert "secret-binary" not in json.dumps(events)


@pytest.mark.django_db
def test_brief_api_emits_creation_event_without_content(caplog):
    caplog.set_level(logging.INFO, logger="ih_design.operations")

    response = APIClient().post(
        "/api/v1/briefs/",
        {
            "title": "Private campaign title",
            "format": "square",
            "audience": "Private audience",
            "objective": "Private objective",
            "requested_message": "Private message",
        },
        format="json",
    )

    assert response.status_code == 201
    event = next(item for item in _events(caplog) if item["event"] == "brief.created")
    assert event["brief_id"] == response.json()["id"]
    assert "Private campaign title" not in json.dumps(event)
