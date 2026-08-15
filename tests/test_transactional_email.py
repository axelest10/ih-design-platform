from __future__ import annotations

import importlib
import json
import logging
import sys
from urllib.error import HTTPError, URLError

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from rest_framework.test import APIClient

from security.models import PasswordResetToken
from security.services.email import (
    EmailDeliveryError,
    EmailDeliverySuppressed,
    send_transactional_email,
)


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _successful_urlopen(captured: dict):
    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({"ErrorCode": 0, "MessageID": "postmark-message-safe-id"})

    return fake_urlopen


@override_settings(
    DJANGO_ENV="staging",
    EMAIL_DELIVERY_MODE="allowlist",
    EMAIL_ALLOWED_RECIPIENTS=("approved-test@example.test",),
    POSTMARK_SERVER_TOKEN="postmark-test-server-token",
    POSTMARK_FROM_EMAIL="mydesign@ihlatam.com",
    POSTMARK_FROM_NAME="IH Design",
    POSTMARK_MESSAGE_STREAM="outbound",
    POSTMARK_REPLY_TO="reply@example.test",
)
def test_postmark_request_uses_expected_transactional_contract(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "security.services.email.urlopen",
        _successful_urlopen(captured),
    )

    message_id = send_transactional_email(
        to="approved-test@example.test",
        subject="Recupera tu acceso a IH Design Platform",
        text_body="Texto seguro",
        html_body="<p>Texto seguro</p>",
        tag="password-reset",
    )

    request = captured["request"]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://api.postmarkapp.com/email"
    assert request.method == "POST"
    assert request.get_header("X-postmark-server-token") == "postmark-test-server-token"
    assert request.get_header("Accept") == "application/json"
    assert captured["timeout"] == 15
    assert payload == {
        "From": "IH Design <mydesign@ihlatam.com>",
        "To": "approved-test@example.test",
        "Subject": "Recupera tu acceso a IH Design Platform",
        "HtmlBody": "<p>Texto seguro</p>",
        "TextBody": "Texto seguro",
        "MessageStream": "outbound",
        "TrackOpens": False,
        "TrackLinks": "None",
        "ReplyTo": "reply@example.test",
        "Tag": "password-reset",
    }
    assert message_id == "postmark-message-safe-id"


@override_settings(
    DJANGO_ENV="staging",
    EMAIL_DELIVERY_MODE="allowlist",
    EMAIL_ALLOWED_RECIPIENTS=("approved-test@example.test",),
    POSTMARK_SERVER_TOKEN="",
    POSTMARK_FROM_EMAIL="mydesign@ihlatam.com",
    POSTMARK_FROM_NAME="IH Design",
    POSTMARK_MESSAGE_STREAM="outbound",
    POSTMARK_REPLY_TO="",
)
def test_missing_postmark_token_fails_without_network(monkeypatch):
    called = False

    def unexpected_urlopen(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("security.services.email.urlopen", unexpected_urlopen)
    with pytest.raises(EmailDeliveryError) as exc_info:
        send_transactional_email(
            to="approved-test@example.test",
            subject="Subject",
            text_body="Text",
            html_body="<p>Text</p>",
        )

    assert exc_info.value.category == "configuration"
    assert called is False


@pytest.mark.parametrize(
    ("allowed", "recipient", "category"),
    [
        ((), "approved-test@example.test", "allowlist_empty"),
        (("approved-test@example.test",), "employee@ihmexico.com", "recipient_not_allowed"),
    ],
)
def test_staging_allowlist_fails_closed(monkeypatch, settings, allowed, recipient, category):
    settings.DJANGO_ENV = "staging"
    settings.EMAIL_DELIVERY_MODE = "allowlist"
    settings.EMAIL_ALLOWED_RECIPIENTS = allowed
    settings.POSTMARK_SERVER_TOKEN = "postmark-test-server-token"
    settings.POSTMARK_FROM_EMAIL = "mydesign@ihlatam.com"
    settings.POSTMARK_FROM_NAME = "IH Design"
    settings.POSTMARK_MESSAGE_STREAM = "outbound"
    settings.POSTMARK_REPLY_TO = ""
    called = False

    def unexpected_urlopen(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("security.services.email.urlopen", unexpected_urlopen)
    with pytest.raises(EmailDeliverySuppressed) as exc_info:
        send_transactional_email(
            to=recipient,
            subject="Subject",
            text_body="Text",
            html_body="<p>Text</p>",
        )

    assert exc_info.value.category == category
    assert called is False


def test_live_delivery_is_forbidden_outside_production(monkeypatch, settings):
    settings.DJANGO_ENV = "staging"
    settings.EMAIL_DELIVERY_MODE = "live"
    settings.EMAIL_ALLOWED_RECIPIENTS = ()
    settings.POSTMARK_SERVER_TOKEN = "postmark-test-server-token"
    settings.POSTMARK_FROM_EMAIL = "mydesign@ihlatam.com"
    settings.POSTMARK_FROM_NAME = "IH Design"
    settings.POSTMARK_MESSAGE_STREAM = "outbound"
    settings.POSTMARK_REPLY_TO = ""
    called = False

    def unexpected_urlopen(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("security.services.email.urlopen", unexpected_urlopen)
    with pytest.raises(EmailDeliverySuppressed) as exc_info:
        send_transactional_email(
            to="employee@ihmexico.com",
            subject="Subject",
            text_body="Text",
            html_body="<p>Text</p>",
        )

    assert exc_info.value.category == "live_mode_forbidden"
    assert called is False


@override_settings(
    DJANGO_ENV="production",
    EMAIL_DELIVERY_MODE="live",
    EMAIL_ALLOWED_RECIPIENTS=(),
    POSTMARK_SERVER_TOKEN="postmark-test-server-token",
    POSTMARK_FROM_EMAIL="mydesign@ihlatam.com",
    POSTMARK_FROM_NAME="IH Design",
    POSTMARK_MESSAGE_STREAM="outbound",
    POSTMARK_REPLY_TO="",
)
def test_production_live_mode_does_not_inherit_staging_allowlist(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "security.services.email.urlopen",
        _successful_urlopen(captured),
    )

    send_transactional_email(
        to="employee@ihmexico.com",
        subject="Subject",
        text_body="Text",
        html_body="<p>Text</p>",
    )

    payload = json.loads(captured["request"].data)
    assert payload["To"] == "employee@ihmexico.com"
    assert "ReplyTo" not in payload


@override_settings(
    DJANGO_ENV="staging",
    EMAIL_DELIVERY_MODE="allowlist",
    EMAIL_ALLOWED_RECIPIENTS=("approved-test@example.test",),
    POSTMARK_SERVER_TOKEN="postmark-test-server-token",
    POSTMARK_FROM_EMAIL="mydesign@ihlatam.com",
    POSTMARK_FROM_NAME="IH Design",
    POSTMARK_MESSAGE_STREAM="outbound",
    POSTMARK_REPLY_TO="",
)
@pytest.mark.parametrize(
    ("error", "category"),
    [
        (
            HTTPError("https://api.postmarkapp.com/email", 422, "rejected", None, None),
            "provider_rejected",
        ),
        (
            HTTPError("https://api.postmarkapp.com/email", 503, "unavailable", None, None),
            "provider_unavailable",
        ),
        (URLError("network unavailable"), "provider_unavailable"),
    ],
)
def test_provider_failures_are_safely_classified(monkeypatch, error, category):
    def failing_urlopen(*args, **kwargs):
        raise error

    monkeypatch.setattr("security.services.email.urlopen", failing_urlopen)
    with pytest.raises(EmailDeliveryError) as exc_info:
        send_transactional_email(
            to="approved-test@example.test",
            subject="Subject",
            text_body="Text",
            html_body="<p>Text</p>",
        )

    assert exc_info.value.category == category
    assert "postmark-test-server-token" not in str(exc_info.value)


@pytest.mark.django_db
@override_settings(
    DJANGO_ENV="staging",
    EMAIL_DELIVERY_MODE="allowlist",
    EMAIL_ALLOWED_RECIPIENTS=("recoverable@ihmexico.com",),
    POSTMARK_SERVER_TOKEN="literal-postmark-server-token",
    POSTMARK_FROM_EMAIL="mydesign@ihlatam.com",
    POSTMARK_FROM_NAME="IH Design",
    POSTMARK_MESSAGE_STREAM="outbound",
    POSTMARK_REPLY_TO="",
)
def test_password_reset_provider_failure_logs_only_safe_category(monkeypatch, caplog):
    user = get_user_model().objects.create_user(
        username="recoverable-postmark-failure",
        email="recoverable@ihmexico.com",
        password="old-password-123",
    )

    def failing_urlopen(*args, **kwargs):
        raise HTTPError(
            "https://api.postmarkapp.com/email",
            422,
            "rejected",
            None,
            None,
        )

    monkeypatch.setattr("security.services.email.urlopen", failing_urlopen)
    caplog.set_level(logging.INFO, logger="ih_design.operations")
    response = APIClient().post(
        "/api/v1/auth/password-reset/request/",
        {"email": user.email},
        format="json",
    )

    assert response.status_code == 202
    assert PasswordResetToken.objects.filter(user=user).count() == 0
    serialized = "\n".join(record.message for record in caplog.records)
    assert "provider_rejected" in serialized
    assert "literal-postmark-server-token" not in serialized
    assert "#reset=" not in serialized
    assert user.email not in serialized


def _reload_settings_module(monkeypatch, env):
    for key in ("DJANGO_ENV", "DJANGO_SECRET_KEY", "EMAIL_DELIVERY_MODE"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    original_module = sys.modules.pop("config.settings", None)
    try:
        return importlib.import_module("config.settings")
    finally:
        sys.modules.pop("config.settings", None)
        if original_module is not None:
            sys.modules["config.settings"] = original_module


def test_settings_reject_live_mode_in_staging(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="solo está permitido"):
        _reload_settings_module(
            monkeypatch,
            {
                "DJANGO_ENV": "staging",
                "DJANGO_SECRET_KEY": "staging-test-secret",
                "EMAIL_DELIVERY_MODE": "live",
            },
        )


def test_settings_accept_live_mode_only_in_production(monkeypatch):
    module = _reload_settings_module(
        monkeypatch,
        {
            "DJANGO_ENV": "production",
            "DJANGO_SECRET_KEY": "production-test-secret",
            "EMAIL_DELIVERY_MODE": "live",
        },
    )

    assert module.EMAIL_DELIVERY_MODE == "live"
    assert module.POSTMARK_FROM_EMAIL == "mydesign@ihlatam.com"
    assert module.POSTMARK_FROM_NAME == "IH Design"
