"""Proveedor central de correo transaccional mediante Postmark."""

from __future__ import annotations

import json
from dataclasses import dataclass
from email.utils import formataddr, parseaddr
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

POSTMARK_EMAIL_URL = "https://api.postmarkapp.com/email"


class EmailDeliveryError(RuntimeError):
    """Postmark no pudo aceptar el correo transaccional."""

    def __init__(self, category: str):
        super().__init__("No fue posible completar el envío de correo transaccional.")
        self.category = category


class EmailDeliverySuppressed(EmailDeliveryError):
    """La política del entorno impidió contactar al proveedor."""


@dataclass(frozen=True)
class EmailMessage:
    recipients: tuple[str, ...]
    subject: str
    html: str
    text: str
    reply_to: str | None = None
    tag: str | None = None


class TransactionalEmailClient(Protocol):
    def send(self, message: EmailMessage) -> str: ...


def _address(value: str) -> str:
    return parseaddr(value)[1].strip().casefold()


def _enforce_delivery_policy(recipients: tuple[str, ...]) -> None:
    mode = settings.EMAIL_DELIVERY_MODE
    if mode == "disabled":
        raise EmailDeliverySuppressed("delivery_disabled")
    if mode == "allowlist":
        allowed = {_address(value) for value in settings.EMAIL_ALLOWED_RECIPIENTS}
        requested = {_address(value) for value in recipients}
        if not allowed:
            raise EmailDeliverySuppressed("allowlist_empty")
        if not requested or "" in requested or not requested.issubset(allowed):
            raise EmailDeliverySuppressed("recipient_not_allowed")
        return
    if mode == "live":
        if settings.DJANGO_ENV != "production":
            raise EmailDeliverySuppressed("live_mode_forbidden")
        return
    raise EmailDeliveryError("configuration")


class PostmarkEmailClient:
    """Único punto que conoce el contrato HTTP de Postmark."""

    def __init__(
        self,
        *,
        server_token: str,
        from_email: str,
        from_name: str,
        message_stream: str,
        default_reply_to: str,
    ):
        self.server_token = server_token
        self.from_email = from_email
        self.from_name = from_name
        self.message_stream = message_stream
        self.default_reply_to = default_reply_to

    def send(self, message: EmailMessage) -> str:
        _enforce_delivery_policy(message.recipients)
        if not self.server_token or not self.from_email or not self.message_stream:
            raise EmailDeliveryError("configuration")

        payload = {
            "From": formataddr((self.from_name, self.from_email)),
            "To": ", ".join(message.recipients),
            "Subject": message.subject,
            "HtmlBody": message.html,
            "TextBody": message.text,
            "MessageStream": self.message_stream,
            "TrackOpens": False,
            "TrackLinks": "None",
        }
        reply_to = (message.reply_to or self.default_reply_to).strip()
        if reply_to:
            payload["ReplyTo"] = reply_to
        if message.tag:
            payload["Tag"] = message.tag

        request = Request(
            POSTMARK_EMAIL_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": self.server_token,
                "User-Agent": "ih-design-platform/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            category = (
                "provider_unavailable"
                if exc.code == 429 or exc.code >= 500
                else "provider_rejected"
            )
            raise EmailDeliveryError(category) from exc
        except (URLError, TimeoutError) as exc:
            raise EmailDeliveryError("provider_unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EmailDeliveryError("invalid_response") from exc

        if response_payload.get("ErrorCode") != 0:
            raise EmailDeliveryError("provider_rejected")
        message_id = str(response_payload.get("MessageID") or "").strip()
        if not message_id:
            raise EmailDeliveryError("invalid_response")
        return message_id


def get_email_client() -> TransactionalEmailClient:
    return PostmarkEmailClient(
        server_token=settings.POSTMARK_SERVER_TOKEN,
        from_email=settings.POSTMARK_FROM_EMAIL,
        from_name=settings.POSTMARK_FROM_NAME,
        message_stream=settings.POSTMARK_MESSAGE_STREAM,
        default_reply_to=settings.POSTMARK_REPLY_TO,
    )


def send_transactional_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: str,
    reply_to: str | None = None,
    tag: str | None = None,
) -> str:
    """Envía un correo sin exponer autenticación o política del proveedor al llamador."""
    return get_email_client().send(
        EmailMessage(
            recipients=(to,),
            subject=subject,
            html=html_body,
            text=text_body,
            reply_to=reply_to,
            tag=tag,
        )
    )
