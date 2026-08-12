"""Emisión y consumo de tokens firmados de recuperación de contraseña."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from security.models import PasswordResetToken
from security.permissions import is_allowed_corporate_email

PASSWORD_RESET_SALT = "security.password-reset.v1"


class PasswordResetError(ValueError):
    """El token no puede autorizar un cambio de contraseña."""


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset(user) -> tuple[str, PasswordResetToken]:
    max_age = settings.PASSWORD_RESET_MAX_AGE_SECONDS
    if max_age <= 0:
        raise PasswordResetError("PASSWORD_RESET_MAX_AGE_SECONDS debe ser mayor que cero.")
    token = signing.dumps(
        {"user_id": user.pk, "email": user.email.casefold(), "nonce": secrets.token_urlsafe(32)},
        salt=PASSWORD_RESET_SALT,
        compress=True,
    )
    record = PasswordResetToken.objects.create(
        token_hash=_token_hash(token),
        user=user,
        expires_at=timezone.now() + timedelta(seconds=max_age),
    )
    return token, record


def invalidate_other_password_resets(record: PasswordResetToken) -> None:
    PasswordResetToken.objects.filter(user=record.user, used_at__isnull=True).exclude(
        pk=record.pk
    ).delete()


@transaction.atomic
def consume_password_reset(token: str, new_password: str):
    try:
        payload = signing.loads(
            token,
            salt=PASSWORD_RESET_SALT,
            max_age=settings.PASSWORD_RESET_MAX_AGE_SECONDS,
        )
    except signing.SignatureExpired as exc:
        raise PasswordResetError("El enlace de recuperación expiró.") from exc
    except signing.BadSignature as exc:
        raise PasswordResetError("El enlace de recuperación no es válido.") from exc

    record = (
        PasswordResetToken.objects.select_for_update()
        .select_related("user")
        .filter(token_hash=_token_hash(token), user_id=payload.get("user_id"))
        .first()
    )
    if record is None or record.used_at is not None:
        raise PasswordResetError("El enlace de recuperación no es válido o ya fue utilizado.")
    if record.expires_at <= timezone.now():
        raise PasswordResetError("El enlace de recuperación expiró.")

    user = record.user
    payload_email = str(payload.get("email") or "").strip().casefold()
    if (
        not user.is_active
        or user.email.casefold() != payload_email
        or not is_allowed_corporate_email(user.email)
    ):
        raise PasswordResetError("El enlace de recuperación ya no es válido.")

    user.set_password(new_password)
    user.save(update_fields=["password"])
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return user
