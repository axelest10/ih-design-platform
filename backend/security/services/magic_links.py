"""Emisión y consumo de tokens firmados para acceso corporativo sin contraseña."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone

from security.models import MagicLinkToken
from security.permissions import is_allowed_corporate_email

MAGIC_LINK_SALT = "security.magic-link.v1"


class MagicLinkError(ValueError):
    """El enlace no puede autenticar una sesión."""


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_magic_link(email: str) -> tuple[str, MagicLinkToken]:
    max_age = settings.MAGIC_LINK_MAX_AGE_SECONDS
    if max_age <= 0:
        raise MagicLinkError("MAGIC_LINK_MAX_AGE_SECONDS debe ser mayor que cero.")
    token = signing.dumps(
        {"email": email, "nonce": secrets.token_urlsafe(32)},
        salt=MAGIC_LINK_SALT,
        compress=True,
    )
    record = MagicLinkToken.objects.create(
        token_hash=_token_hash(token),
        email=email,
        expires_at=timezone.now() + timedelta(seconds=max_age),
    )
    return token, record


def invalidate_other_magic_links(record: MagicLinkToken) -> None:
    MagicLinkToken.objects.filter(email=record.email, used_at__isnull=True).exclude(
        pk=record.pk
    ).delete()


def _username_for_email(email: str) -> str:
    user_model = get_user_model()
    if len(email) <= user_model._meta.get_field("username").max_length:
        if not user_model.objects.filter(username=email).exists():
            return email
    return f"magic-{hashlib.sha256(email.encode('utf-8')).hexdigest()[:32]}"


@transaction.atomic
def consume_magic_link(token: str):
    try:
        payload = signing.loads(
            token,
            salt=MAGIC_LINK_SALT,
            max_age=settings.MAGIC_LINK_MAX_AGE_SECONDS,
        )
    except signing.SignatureExpired as exc:
        raise MagicLinkError("El enlace de acceso expiró.") from exc
    except signing.BadSignature as exc:
        raise MagicLinkError("El enlace de acceso no es válido.") from exc

    email = str(payload.get("email") or "").strip().casefold()
    if not is_allowed_corporate_email(email):
        raise MagicLinkError("El dominio del enlace ya no está autorizado.")

    record = (
        MagicLinkToken.objects.select_for_update()
        .filter(token_hash=_token_hash(token), email=email)
        .first()
    )
    if record is None:
        raise MagicLinkError("El enlace de acceso no es válido.")
    if record.used_at is not None:
        raise MagicLinkError("El enlace de acceso ya fue utilizado.")
    if record.expires_at <= timezone.now():
        raise MagicLinkError("El enlace de acceso expiró.")

    user_model = get_user_model()
    user = user_model.objects.filter(email__iexact=email).first()
    if user is None:
        user = user_model.objects.create_user(
            username=_username_for_email(email),
            email=email,
            password=None,
        )

    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return user
