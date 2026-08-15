"""Endpoint público acotado para webhooks autenticados de Postmark."""

from __future__ import annotations

import base64
import binascii
import hmac
import json

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from common.observability import operation_event

from .services.postmark_webhook import InvalidPostmarkWebhook, process_postmark_webhook


def _authenticated(request) -> bool:
    expected_username = settings.POSTMARK_WEBHOOK_USERNAME
    expected_password = settings.POSTMARK_WEBHOOK_PASSWORD
    if not expected_username or not expected_password:
        return False
    header = request.headers.get("Authorization", "")
    scheme, separator, encoded = header.partition(" ")
    if not separator or scheme.casefold() != "basic":
        return False
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, separator, password = decoded.partition(":")
    if not separator:
        return False
    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(
        password, expected_password
    )


@csrf_exempt
@require_POST
def postmark_webhook(request):
    if not settings.POSTMARK_WEBHOOK_USERNAME or not settings.POSTMARK_WEBHOOK_PASSWORD:
        operation_event(
            "email.postmark_webhook",
            status="unavailable",
            reason="authentication_not_configured",
            http_status=503,
        )
        return JsonResponse({"detail": "Webhook unavailable."}, status=503)
    if not _authenticated(request):
        operation_event(
            "email.postmark_webhook",
            status="rejected",
            reason="invalid_authentication",
            http_status=403,
        )
        return JsonResponse({"detail": "Forbidden."}, status=403)

    content_length = request.META.get("CONTENT_LENGTH", "")
    if content_length.isdigit() and int(content_length) > settings.POSTMARK_WEBHOOK_MAX_BYTES:
        return JsonResponse({"detail": "Payload too large."}, status=413)
    try:
        raw_body = request.body
    except RequestDataTooBig:
        return JsonResponse({"detail": "Payload too large."}, status=413)
    if len(raw_body) > settings.POSTMARK_WEBHOOK_MAX_BYTES:
        return JsonResponse({"detail": "Payload too large."}, status=413)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"detail": "Malformed payload."}, status=400)

    try:
        result = process_postmark_webhook(payload)
    except InvalidPostmarkWebhook as exc:
        operation_event(
            "email.postmark_webhook",
            status="rejected",
            reason=str(exc),
            http_status=400,
        )
        return JsonResponse({"detail": "Invalid payload."}, status=400)

    operation_event(
        "email.postmark_webhook",
        status="ignored" if result.ignored else "accepted",
        provider="postmark",
        event_type=result.event_type,
        provider_event_id=result.provider_event_id,
        email_delivery_id=result.delivery_id,
        duplicate=result.duplicate,
        http_status=200,
    )
    return JsonResponse(
        {"accepted": not result.ignored, "duplicate": result.duplicate},
        status=200,
    )
