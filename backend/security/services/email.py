"""Adaptador mínimo para correo transaccional mediante la API HTTP de Resend."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

RESEND_EMAILS_URL = "https://api.resend.com/emails"


class EmailDeliveryError(RuntimeError):
    """El proveedor no aceptó el correo transaccional."""


@dataclass(frozen=True)
class EmailMessage:
    sender: str
    recipients: tuple[str, ...]
    subject: str
    html: str
    text: str


class TransactionalEmailClient(Protocol):
    def send(self, message: EmailMessage) -> str:
        ...


class ResendEmailClient:
    """Único punto que conoce el contrato HTTP de Resend."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def send(self, message: EmailMessage) -> str:
        if not self.api_key:
            raise EmailDeliveryError("RESEND_API_KEY no está configurada.")
        payload = {
            "from": message.sender,
            "to": list(message.recipients),
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        request = Request(
            RESEND_EMAILS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ih-design-platform/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise EmailDeliveryError(f"Resend rechazó el correo con HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise EmailDeliveryError("No fue posible completar el envío con Resend.") from exc

        email_id = str(response_payload.get("id") or "").strip()
        if not email_id:
            raise EmailDeliveryError("Resend no devolvió el identificador del correo.")
        return email_id


def get_email_client() -> TransactionalEmailClient:
    return ResendEmailClient(settings.RESEND_API_KEY)
