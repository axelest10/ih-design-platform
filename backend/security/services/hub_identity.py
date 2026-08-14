from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from security.models import HubIdentity, HubIdentityEvent
from security.permissions import ROLE_VIEWER

PROHIBITED_IDENTITY_CLAIMS = {
    "branch",
    "center",
    "centre",
    "country",
    "group",
    "groups",
    "hub_roles",
    "hub_permissions",
    "org",
    "org_id",
    "organisation",
    "organization",
    "permissions",
    "role",
    "roles",
    "school",
    "tenant_id",
    "tenantId",
}


class HubIdentityError(Exception):
    reason = "identity_denied"


class InvalidHubClaims(HubIdentityError):
    reason = "invalid_claims"


class HubIdentityConflict(HubIdentityError):
    reason = "identity_conflict"


class InactiveDesignUser(HubIdentityError):
    reason = "inactive_design_user"


@dataclass(frozen=True)
class ValidatedHubClaims:
    subject: str
    email: str
    name: str


@dataclass(frozen=True)
class HubIdentityResolution:
    user: object
    identity: HubIdentity
    link_source: str


def validate_hub_claims(raw_claims: Mapping[str, object]) -> ValidatedHubClaims:
    if PROHIBITED_IDENTITY_CLAIMS.intersection(raw_claims):
        raise InvalidHubClaims("El proveedor envió claims fuera del contrato de identidad.")

    subject = str(raw_claims.get("sub") or "").strip()
    email = str(raw_claims.get("email") or "").strip().casefold()
    name = str(raw_claims.get("name") or "").strip()
    if not subject or len(subject) > 255 or any(ord(character) < 32 for character in subject):
        raise InvalidHubClaims("El subject del Hub no es válido.")
    if raw_claims.get("email_verified") is not True:
        raise InvalidHubClaims("El Hub no verificó el correo.")
    try:
        validate_email(email)
    except ValidationError as exc:
        raise InvalidHubClaims("El correo del Hub no es válido.") from exc
    if len(name) > 150:
        raise InvalidHubClaims("El nombre del Hub excede el contrato.")
    return ValidatedHubClaims(subject=subject, email=email, name=name)


def resolve_hub_identity(raw_claims: Mapping[str, object]) -> HubIdentityResolution:
    subject_for_audit = _safe_subject(raw_claims.get("sub"))
    try:
        claims = validate_hub_claims(raw_claims)
        with transaction.atomic():
            return _resolve_hub_identity(claims)
    except HubIdentityError as exc:
        record_hub_identity_denial(subject_for_audit, exc.reason)
        raise
    except IntegrityError as exc:
        record_hub_identity_denial(subject_for_audit, HubIdentityConflict.reason)
        raise HubIdentityConflict("El enlace de identidad entró en conflicto.") from exc


def _resolve_hub_identity(claims: ValidatedHubClaims) -> HubIdentityResolution:
    now = timezone.now()
    identity = (
        HubIdentity.objects.select_for_update()
        .select_related("user")
        .filter(hub_subject=claims.subject)
        .first()
    )
    if identity:
        user = identity.user
        _assert_active(user)
        email_update = _refresh_email_attribute(user, claims.email)
        identity.email_snapshot = claims.email
        identity.last_authenticated_at = now
        identity.save(update_fields=["email_snapshot", "last_authenticated_at"])
        _record_success(
            HubIdentityEvent.EventType.LOGIN_SUCCESS,
            user,
            claims.subject,
            {"link_source": identity.link_source, "email_update": email_update},
        )
        return HubIdentityResolution(
            user=user,
            identity=identity,
            link_source=identity.link_source,
        )

    user_model = get_user_model()
    email_matches = list(
        user_model.objects.select_for_update().filter(email__iexact=claims.email).order_by("pk")[:2]
    )
    if len(email_matches) > 1:
        raise HubIdentityConflict("El correo coincide con múltiples cuentas locales.")

    if email_matches:
        user = email_matches[0]
        _assert_active(user)
        if HubIdentity.objects.select_for_update().filter(user=user).exists():
            raise HubIdentityConflict("La cuenta local ya está enlazada a otro subject.")
        link_source = HubIdentity.LinkSource.LINKED_EXISTING
        event_type = HubIdentityEvent.EventType.LINKED
    else:
        user = _provision_viewer(claims)
        link_source = HubIdentity.LinkSource.PROVISIONED
        event_type = HubIdentityEvent.EventType.PROVISIONED

    identity = HubIdentity.objects.create(
        user=user,
        hub_subject=claims.subject,
        initial_email=claims.email,
        email_snapshot=claims.email,
        link_source=link_source,
        last_authenticated_at=now,
    )
    _record_success(event_type, user, claims.subject, {"link_source": link_source})
    _record_success(
        HubIdentityEvent.EventType.LOGIN_SUCCESS,
        user,
        claims.subject,
        {"link_source": link_source},
    )
    return HubIdentityResolution(user=user, identity=identity, link_source=link_source)


def _provision_viewer(claims: ValidatedHubClaims):
    user_model = get_user_model()
    local_part = claims.email.partition("@")[0]
    stem = slugify(local_part)[:100] or "hub-user"
    digest = sha256(claims.subject.encode("utf-8")).hexdigest()
    username = f"{stem}-{digest[:12]}"
    if user_model.objects.filter(username=username).exists():
        username = f"{stem[:91]}-{digest[:20]}"

    user = user_model(username=username, email=claims.email, first_name=claims.name)
    user.set_unusable_password()
    user.save()
    viewer, _ = Group.objects.get_or_create(name=ROLE_VIEWER)
    user.groups.add(viewer)
    return user


def _refresh_email_attribute(user, email: str) -> str:
    if user.email.casefold() == email:
        return "unchanged"
    conflict = get_user_model().objects.filter(email__iexact=email).exclude(pk=user.pk).exists()
    if conflict:
        return "conflict_preserved_local"
    user.email = email
    user.save(update_fields=["email"])
    return "updated"


def _assert_active(user) -> None:
    if not user.is_active:
        raise InactiveDesignUser("La cuenta local está inactiva.")


def _record_success(event_type: str, user, subject: str, metadata: dict[str, object]) -> None:
    HubIdentityEvent.objects.create(
        event_type=event_type,
        outcome=HubIdentityEvent.Outcome.SUCCESS,
        user=user,
        hub_subject=subject,
        metadata=metadata,
    )


def record_hub_identity_denial(subject: str, reason: str) -> None:
    try:
        HubIdentityEvent.objects.create(
            event_type=HubIdentityEvent.EventType.LOGIN_DENIED,
            outcome=HubIdentityEvent.Outcome.DENIED,
            hub_subject=subject,
            reason=reason,
        )
    except Exception:
        # Authentication errors never reveal whether audit persistence succeeded.
        return


def _safe_subject(value: object) -> str:
    subject = str(value or "").strip()
    if len(subject) > 255 or any(ord(character) < 32 for character in subject):
        return ""
    return subject
