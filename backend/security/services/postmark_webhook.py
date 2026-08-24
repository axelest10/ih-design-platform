"""Validación y persistencia idempotente de webhooks transaccionales de Postmark."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from security.models import (
    EmailRecipientState,
    PostmarkWebhookEvent,
    TransactionalEmailDelivery,
)

SUPPORTED_EVENT_TYPES = {choice for choice, _label in PostmarkWebhookEvent.EventType.choices}
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
SECRET_PATTERN = re.compile(r"(?i)\b(token|reset|secret|password)\s*[:=]\s*[^\s,;]+")


class InvalidPostmarkWebhook(ValueError):
    """El payload no satisface el contrato mínimo del evento declarado."""


@dataclass(frozen=True)
class WebhookResult:
    event_type: str
    provider_event_id: str = ""
    delivery_id: int | None = None
    duplicate: bool = False
    ignored: bool = False


def _required_text(payload: dict[str, Any], key: str, *, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidPostmarkWebhook(f"missing_or_invalid_{key}")
    value = value.strip()
    if len(value) > max_length:
        raise InvalidPostmarkWebhook(f"invalid_{key}")
    return value


def _optional_text(payload: dict[str, Any], key: str, *, max_length: int) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, (str, int)):
        raise InvalidPostmarkWebhook(f"invalid_{key}")
    value = str(value).strip()
    if len(value) > max_length:
        raise InvalidPostmarkWebhook(f"invalid_{key}")
    return value


def _recipient(payload: dict[str, Any], event_type: str) -> str:
    key = (
        "Email"
        if event_type
        in {
            PostmarkWebhookEvent.EventType.BOUNCE,
            PostmarkWebhookEvent.EventType.SPAM_COMPLAINT,
        }
        else "Recipient"
    )
    recipient = _required_text(payload, key, max_length=254).casefold()
    try:
        validate_email(recipient)
    except ValidationError as exc:
        raise InvalidPostmarkWebhook(f"invalid_{key}") from exc
    return recipient


def _occurred_at(payload: dict[str, Any], event_type: str):
    timestamp_key = {
        PostmarkWebhookEvent.EventType.DELIVERY: "DeliveredAt",
        PostmarkWebhookEvent.EventType.BOUNCE: "BouncedAt",
        PostmarkWebhookEvent.EventType.SPAM_COMPLAINT: "BouncedAt",
        PostmarkWebhookEvent.EventType.SUBSCRIPTION_CHANGE: "ChangedAt",
    }[event_type]
    value = _required_text(payload, timestamp_key, max_length=64)
    parsed = parse_datetime(value)
    if parsed is None or not timezone.is_aware(parsed):
        raise InvalidPostmarkWebhook(f"invalid_{timestamp_key}")
    return parsed


def _safe_detail(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    safe = " ".join(value.replace("\x00", " ").split())
    safe = EMAIL_PATTERN.sub("[redacted-email]", safe)
    safe = URL_PATTERN.sub("[redacted-url]", safe)
    safe = SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[redacted]", safe)
    return safe[:500]


def _event_identity(
    *,
    event_type: str,
    provider_event_id: str,
    provider_message_id: str,
    recipient: str,
    occurred_at,
    classification: str,
    suppress_sending: bool | None,
) -> str:
    if provider_event_id:
        identity = [event_type, provider_event_id]
    else:
        identity = [
            event_type,
            provider_message_id,
            recipient,
            occurred_at.isoformat(),
            classification,
            suppress_sending,
        ]
    canonical = json.dumps(identity, ensure_ascii=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _delivery_from_metadata(payload: dict[str, Any]):
    metadata = payload.get("Metadata")
    if not isinstance(metadata, dict):
        return None
    raw_delivery_id = metadata.get("email_delivery_id")
    if not isinstance(raw_delivery_id, (str, int)) or not str(raw_delivery_id).isdigit():
        return None
    return TransactionalEmailDelivery.objects.filter(pk=int(raw_delivery_id)).first()


def _find_delivery(
    payload: dict[str, Any],
    *,
    event_type: str,
    provider_message_id: str,
    recipient: str,
):
    delivery = None
    if provider_message_id:
        delivery = TransactionalEmailDelivery.objects.filter(
            provider_message_id=provider_message_id
        ).first()
    if delivery is None and event_type != PostmarkWebhookEvent.EventType.SUBSCRIPTION_CHANGE:
        delivery = _delivery_from_metadata(payload)
    if delivery is None and event_type == PostmarkWebhookEvent.EventType.SUBSCRIPTION_CHANGE:
        if provider_message_id:
            return None
        delivery = (
            TransactionalEmailDelivery.objects.filter(recipient__iexact=recipient)
            .order_by("-submitted_at")
            .first()
        )
    if delivery is not None and delivery.recipient.casefold() != recipient:
        return None
    return delivery


def _event_fields(payload: dict[str, Any], event_type: str):
    provider_event_id = _optional_text(payload, "ID", max_length=64)
    if provider_event_id and not provider_event_id.isdigit():
        raise InvalidPostmarkWebhook("invalid_ID")
    provider_message_id = _optional_text(payload, "MessageID", max_length=64)
    if event_type != PostmarkWebhookEvent.EventType.SUBSCRIPTION_CHANGE:
        if not provider_message_id:
            raise InvalidPostmarkWebhook("missing_or_invalid_MessageID")

    recipient = _recipient(payload, event_type)
    occurred_at = _occurred_at(payload, event_type)
    message_stream = _optional_text(payload, "MessageStream", max_length=64)
    suppress_sending = None

    if event_type == PostmarkWebhookEvent.EventType.DELIVERY:
        classification = "delivered"
        detail = _safe_detail(payload.get("Details"))
    elif event_type == PostmarkWebhookEvent.EventType.BOUNCE:
        classification = _required_text(payload, "Type", max_length=64)
        detail = _safe_detail(payload.get("Details") or payload.get("Description"))
    elif event_type == PostmarkWebhookEvent.EventType.SPAM_COMPLAINT:
        classification = "spam_complaint"
        detail = "Spam complaint"
    else:
        if not isinstance(payload.get("SuppressSending"), bool):
            raise InvalidPostmarkWebhook("missing_or_invalid_SuppressSending")
        suppress_sending = payload["SuppressSending"]
        if suppress_sending:
            classification = _required_text(payload, "SuppressionReason", max_length=64)
            if classification not in {"HardBounce", "SpamComplaint", "ManualSuppression"}:
                raise InvalidPostmarkWebhook("invalid_SuppressionReason")
        else:
            if payload.get("SuppressionReason") is not None:
                raise InvalidPostmarkWebhook("invalid_SuppressionReason")
            classification = "reactivated"
        detail = _safe_detail(payload.get("Origin"))

    return {
        "provider_event_id": provider_event_id,
        "provider_message_id": provider_message_id,
        "recipient": recipient,
        "occurred_at": occurred_at,
        "message_stream": message_stream,
        "classification": classification,
        "safe_detail": detail,
        "suppress_sending": suppress_sending,
    }


def _apply_event(delivery, recipient_state, payload, event_type, fields):
    occurred_at = fields["occurred_at"]
    if delivery.last_event_at and occurred_at < delivery.last_event_at:
        return

    delivery.last_event_at = occurred_at
    recipient_event_is_current = (
        recipient_state.provider_changed_at is None
        or occurred_at >= recipient_state.provider_changed_at
    )
    if not delivery.provider_message_id and fields["provider_message_id"]:
        delivery.provider_message_id = fields["provider_message_id"]
    if not delivery.message_stream and fields["message_stream"]:
        delivery.message_stream = fields["message_stream"]

    if event_type == PostmarkWebhookEvent.EventType.DELIVERY:
        delivery.status = TransactionalEmailDelivery.Status.DELIVERED
        delivery.delivered_at = occurred_at
        delivery.safe_reason = fields["safe_detail"]
    elif event_type == PostmarkWebhookEvent.EventType.BOUNCE:
        inactive = payload.get("Inactive") is True
        type_code = payload.get("TypeCode")
        hard_bounce = type_code == 1 or inactive
        delivery.status = TransactionalEmailDelivery.Status.BOUNCED
        delivery.bounce_type = fields["classification"]
        delivery.bounce_type_code = (
            type_code if isinstance(type_code, int) and type_code >= 0 else None
        )
        delivery.failure_category = "hard_non_retryable" if hard_bounce else "transient"
        delivery.safe_reason = fields["safe_detail"]
        if hard_bounce:
            delivery.suppressed = True
            if recipient_event_is_current:
                recipient_state.suppressed = True
                recipient_state.suppression_reason = fields["classification"]
                recipient_state.provider_changed_at = occurred_at
    elif event_type == PostmarkWebhookEvent.EventType.SPAM_COMPLAINT:
        delivery.status = TransactionalEmailDelivery.Status.SPAM_COMPLAINT
        delivery.failure_category = "spam_complaint"
        delivery.safe_reason = fields["safe_detail"]
        delivery.suppressed = True
        delivery.spam_complaint = True
        if recipient_event_is_current:
            recipient_state.suppressed = True
            recipient_state.spam_complaint = True
            recipient_state.suppression_reason = "SpamComplaint"
            recipient_state.provider_changed_at = occurred_at
    else:
        suppress_sending = fields["suppress_sending"]
        delivery.status = (
            TransactionalEmailDelivery.Status.SUPPRESSED
            if suppress_sending
            else TransactionalEmailDelivery.Status.REACTIVATED
        )
        delivery.suppressed = suppress_sending
        delivery.safe_reason = fields["safe_detail"]
        if recipient_event_is_current:
            recipient_state.suppressed = suppress_sending
            recipient_state.suppression_reason = (
                fields["classification"] if suppress_sending else ""
            )
            recipient_state.provider_changed_at = occurred_at

    delivery.save()
    recipient_state.save()


def process_postmark_webhook(payload: Any) -> WebhookResult:
    """Persiste un evento conocido una sola vez; ignora eventos ajenos de forma segura."""
    if not isinstance(payload, dict):
        raise InvalidPostmarkWebhook("payload_must_be_object")
    event_type = payload.get("RecordType")
    if not isinstance(event_type, str) or not event_type:
        raise InvalidPostmarkWebhook("missing_or_invalid_RecordType")
    if event_type not in SUPPORTED_EVENT_TYPES:
        return WebhookResult(event_type="unknown", ignored=True)

    fields = _event_fields(payload, event_type)
    delivery = _find_delivery(
        payload,
        event_type=event_type,
        **{key: fields[key] for key in ("provider_message_id", "recipient")},
    )
    if delivery is None:
        return WebhookResult(
            event_type=event_type,
            provider_event_id=fields["provider_event_id"],
            ignored=True,
        )

    if not fields["message_stream"]:
        fields["message_stream"] = delivery.message_stream
    event_key = _event_identity(
        event_type=event_type,
        **{
            key: fields[key]
            for key in (
                "provider_event_id",
                "provider_message_id",
                "recipient",
                "occurred_at",
                "classification",
                "suppress_sending",
            )
        },
    )

    with transaction.atomic():
        delivery = TransactionalEmailDelivery.objects.select_for_update().get(pk=delivery.pk)
        event, created = PostmarkWebhookEvent.objects.get_or_create(
            event_key=event_key,
            defaults={
                "delivery": delivery,
                "event_type": event_type,
                **fields,
            },
        )
        if not created:
            return WebhookResult(
                event_type=event_type,
                provider_event_id=fields["provider_event_id"],
                delivery_id=delivery.pk,
                duplicate=True,
            )
        recipient_state, _created = EmailRecipientState.objects.select_for_update().get_or_create(
            recipient=fields["recipient"]
        )
        _apply_event(delivery, recipient_state, payload, event_type, fields)

    return WebhookResult(
        event_type=event.event_type,
        provider_event_id=event.provider_event_id,
        delivery_id=delivery.pk,
    )
