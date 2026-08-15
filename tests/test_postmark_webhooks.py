from __future__ import annotations

import base64
import json
import logging

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from security.models import (
    EmailRecipientState,
    PostmarkWebhookEvent,
    TransactionalEmailDelivery,
)

pytestmark = pytest.mark.django_db

WEBHOOK_URL = "/api/v1/webhooks/postmark/"
RECIPIENT = "synthetic-postmark@ihmexico.com"
MESSAGE_ID = "00000000-0000-4000-8000-000000000001"


def _authorization(username="staging-webhook", password="staging-secret"):
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {encoded}"


def _delivery(*, provider_message_id=MESSAGE_ID):
    return TransactionalEmailDelivery.objects.create(
        provider_message_id=provider_message_id,
        recipient=RECIPIENT,
        message_stream="outbound",
        tag="password-reset",
        status=TransactionalEmailDelivery.Status.ACCEPTED,
    )


def _post(payload, *, authorization=None, client=None):
    client = client or APIClient()
    return client.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_AUTHORIZATION=authorization or _authorization(),
    )


def _delivery_payload(**overrides):
    payload = {
        "RecordType": "Delivery",
        "MessageID": MESSAGE_ID,
        "Recipient": RECIPIENT,
        "DeliveredAt": "2026-08-15T12:00:00Z",
        "Details": "Delivered to receiving server",
        "MessageStream": "outbound",
    }
    payload.update(overrides)
    return payload


def _bounce_payload(**overrides):
    payload = {
        "RecordType": "Bounce",
        "ID": 2677000001,
        "Type": "HardBounce",
        "TypeCode": 1,
        "MessageID": MESSAGE_ID,
        "Email": RECIPIENT,
        "BouncedAt": "2026-08-15T12:01:00Z",
        "Inactive": True,
        "CanActivate": True,
        "Details": "The receiving server rejected the recipient",
        "MessageStream": "outbound",
    }
    payload.update(overrides)
    return payload


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
    POSTMARK_WEBHOOK_MAX_BYTES=65536,
)
def test_delivery_event_marks_message_delivered_and_handles_fast_webhook_race():
    delivery = _delivery(provider_message_id=None)
    payload = _delivery_payload(Metadata={"email_delivery_id": str(delivery.pk)})

    response = _post(payload, client=APIClient(enforce_csrf_checks=True))

    assert response.status_code == 200
    assert response.json() == {"accepted": True, "duplicate": False}
    delivery.refresh_from_db()
    assert delivery.provider_message_id == MESSAGE_ID
    assert delivery.status == TransactionalEmailDelivery.Status.DELIVERED
    assert delivery.delivered_at.isoformat() == "2026-08-15T12:00:00+00:00"
    event = PostmarkWebhookEvent.objects.get()
    assert event.delivery == delivery
    assert event.event_type == PostmarkWebhookEvent.EventType.DELIVERY
    assert event.recipient == RECIPIENT
    assert event.message_stream == "outbound"


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_hard_bounce_marks_delivery_and_recipient_suppressed():
    delivery = _delivery()

    response = _post(_bounce_payload())

    assert response.status_code == 200
    delivery.refresh_from_db()
    assert delivery.status == TransactionalEmailDelivery.Status.BOUNCED
    assert delivery.failure_category == "hard_non_retryable"
    assert delivery.bounce_type == "HardBounce"
    assert delivery.bounce_type_code == 1
    assert delivery.suppressed is True
    state = EmailRecipientState.objects.get(recipient=RECIPIENT)
    assert state.suppressed is True
    assert state.suppression_reason == "HardBounce"


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_transient_bounce_does_not_suppress_or_retry():
    delivery = _delivery()

    response = _post(
        _bounce_payload(
            ID=2677000002,
            Type="Transient",
            TypeCode=4096,
            Inactive=False,
            CanActivate=False,
        )
    )

    assert response.status_code == 200
    delivery.refresh_from_db()
    assert delivery.status == TransactionalEmailDelivery.Status.BOUNCED
    assert delivery.failure_category == "transient"
    assert delivery.suppressed is False
    assert EmailRecipientState.objects.get(recipient=RECIPIENT).suppressed is False
    assert TransactionalEmailDelivery.objects.count() == 1


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_spam_complaint_is_persisted_and_suppresses_future_mail():
    delivery = _delivery()
    payload = {
        "RecordType": "SpamComplaint",
        "ID": 2677000003,
        "Type": "SpamComplaint",
        "TypeCode": 512,
        "MessageID": MESSAGE_ID,
        "Email": RECIPIENT,
        "BouncedAt": "2026-08-15T12:02:00Z",
        "Inactive": True,
        "CanActivate": False,
        "MessageStream": "outbound",
    }

    response = _post(payload)

    assert response.status_code == 200
    delivery.refresh_from_db()
    assert delivery.status == TransactionalEmailDelivery.Status.SPAM_COMPLAINT
    assert delivery.spam_complaint is True
    assert delivery.suppressed is True
    state = EmailRecipientState.objects.get(recipient=RECIPIENT)
    assert state.spam_complaint is True
    assert state.suppressed is True


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_subscription_change_suppression_then_reactivation():
    delivery = _delivery()
    suppressed = {
        "RecordType": "SubscriptionChange",
        "MessageID": MESSAGE_ID,
        "Recipient": RECIPIENT,
        "MessageStream": "outbound",
        "SuppressionReason": "ManualSuppression",
        "SuppressSending": True,
        "Origin": "Recipient",
        "ChangedAt": "2026-08-15T12:03:00Z",
    }
    reactivated = {
        **suppressed,
        "MessageID": None,
        "SuppressSending": False,
        "SuppressionReason": None,
        "Origin": "Customer",
        "ChangedAt": "2026-08-15T12:04:00Z",
    }

    first = _post(suppressed)
    delivery.refresh_from_db()
    state = EmailRecipientState.objects.get(recipient=RECIPIENT)
    assert first.status_code == 200
    assert delivery.status == TransactionalEmailDelivery.Status.SUPPRESSED
    assert state.suppressed is True

    second = _post(reactivated)
    delivery.refresh_from_db()
    state.refresh_from_db()
    assert second.status_code == 200
    assert delivery.status == TransactionalEmailDelivery.Status.REACTIVATED
    assert delivery.suppressed is False
    assert state.suppressed is False
    assert state.suppression_reason == ""


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_invalid_authentication_is_rejected_without_persistence(caplog):
    _delivery()
    caplog.set_level(logging.INFO, logger="ih_design.operations")

    response = _post(
        _delivery_payload(),
        authorization=_authorization(password="literal-invalid-secret"),
    )

    assert response.status_code == 403
    assert PostmarkWebhookEvent.objects.count() == 0
    assert "literal-invalid-secret" not in caplog.text


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="",
    POSTMARK_WEBHOOK_PASSWORD="",
)
def test_missing_webhook_credentials_fail_closed():
    _delivery()

    response = _post(_delivery_payload())

    assert response.status_code == 503
    assert PostmarkWebhookEvent.objects.count() == 0


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
@pytest.mark.parametrize("raw_body", [b"not-json", b"[]"])
def test_malformed_json_or_non_object_payload_is_rejected(raw_body):
    response = APIClient().post(
        WEBHOOK_URL,
        data=raw_body,
        content_type="application/json",
        HTTP_AUTHORIZATION=_authorization(),
    )

    assert response.status_code == 400
    assert PostmarkWebhookEvent.objects.count() == 0


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_unknown_event_type_is_acknowledged_and_ignored():
    response = _post({"RecordType": "Open", "MessageID": MESSAGE_ID})

    assert response.status_code == 200
    assert response.json() == {"accepted": False, "duplicate": False}
    assert PostmarkWebhookEvent.objects.count() == 0


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_duplicate_webhook_replay_is_idempotent():
    delivery = _delivery()
    payload = _delivery_payload()

    first = _post(payload)
    second = _post(payload)

    assert first.json() == {"accepted": True, "duplicate": False}
    assert second.json() == {"accepted": True, "duplicate": True}
    assert PostmarkWebhookEvent.objects.count() == 1
    assert TransactionalEmailDelivery.objects.get(pk=delivery.pk).status == "delivered"


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_missing_message_id_is_rejected():
    _delivery()
    response = _post(_delivery_payload(MessageID=None))

    assert response.status_code == 400
    assert PostmarkWebhookEvent.objects.count() == 0


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_event_for_unknown_local_message_is_acknowledged_without_state():
    response = _post(_delivery_payload())

    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert PostmarkWebhookEvent.objects.count() == 0
    assert EmailRecipientState.objects.count() == 0


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
)
def test_message_content_reset_url_and_secrets_are_not_persisted_or_logged(caplog):
    delivery = _delivery()
    reset_token = "literal-reset-token-that-must-not-leak"
    payload = _delivery_payload(
        Details=f"Delivered; token={reset_token} to {RECIPIENT}",
        Subject="Secret password reset",
        TextBody=f"https://staging.example.test/login.html#reset={reset_token}",
        HtmlBody=f'<a href="https://staging.example.test/#reset={reset_token}">Reset</a>',
    )
    caplog.set_level(logging.INFO, logger="ih_design.operations")

    response = _post(payload)

    assert response.status_code == 200
    event = PostmarkWebhookEvent.objects.get(delivery=delivery)
    serialized_event = " ".join(
        [event.safe_detail, event.classification, event.provider_message_id]
    )
    assert reset_token not in serialized_event
    assert RECIPIENT not in event.safe_detail
    assert "#reset=" not in event.safe_detail
    assert reset_token not in caplog.text
    assert RECIPIENT not in caplog.text
    assert "#reset=" not in caplog.text


@override_settings(
    POSTMARK_WEBHOOK_USERNAME="staging-webhook",
    POSTMARK_WEBHOOK_PASSWORD="staging-secret",
    POSTMARK_WEBHOOK_MAX_BYTES=64,
)
def test_request_size_limit_rejects_oversized_payload():
    response = _post(_delivery_payload(Details="x" * 100))

    assert response.status_code == 413
    assert PostmarkWebhookEvent.objects.count() == 0
