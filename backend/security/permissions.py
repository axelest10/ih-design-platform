"""Permisos de acceso corporativo para la API."""

from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings
from rest_framework.permissions import BasePermission

ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_MARKETING = "marketing"
ROLE_DESIGNER = "designer"
ROLE_REVIEWER = "reviewer"
ROLE_VIEWER = "viewer"
CORPORATE_ROLES = (
    ROLE_PLATFORM_ADMIN,
    ROLE_MARKETING,
    ROLE_DESIGNER,
    ROLE_REVIEWER,
    ROLE_VIEWER,
)


def normalize_email_domain(value: str) -> str:
    """Normaliza un dominio sin aceptar URLs ni comodines."""
    return value.strip().casefold().lstrip("@").rstrip(".")


def is_allowed_corporate_email(email: str, allowed_domains: Iterable[str] | None = None) -> bool:
    """Comprueba el dominio exacto de un email ya validado por el proveedor de identidad."""
    normalized_email = str(email or "").strip().casefold()
    local_part, separator, domain = normalized_email.rpartition("@")
    if not separator or not local_part or not domain or "@" in domain:
        return False

    configured_domains = allowed_domains
    if configured_domains is None:
        configured_domains = getattr(settings, "CORPORATE_ALLOWED_EMAIL_DOMAINS", ())
    allowed = {normalize_email_domain(item) for item in configured_domains if item}
    return domain == normalize_email_domain(domain) and domain in allowed


def is_platform_admin_user(user) -> bool:
    """Aplica el mismo criterio administrativo en API y capacidades del frontend."""
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name=ROLE_PLATFORM_ADMIN).exists()
        )
    )


def can_create_briefs_user(user) -> bool:
    """Centraliza la capacidad que también expone GET /me/ al frontend."""
    return bool(
        user
        and user.is_authenticated
        and (
            is_platform_admin_user(user)
            or user.groups.filter(name__in=(ROLE_MARKETING, ROLE_DESIGNER)).exists()
        )
    )


def is_verified_hub_session(request, user) -> bool:
    """Verify server-side that an OIDC session still has its subject link."""
    from security.models import HubIdentity
    from security.session_contract import (
        AUTH_METHOD_SESSION_KEY,
        HUB_AUTH_METHOD,
        HUB_SUBJECT_SESSION_KEY,
    )

    if not user or not user.is_authenticated:
        return False
    if request.session.get(AUTH_METHOD_SESSION_KEY) != HUB_AUTH_METHOD:
        return False
    subject = request.session.get(HUB_SUBJECT_SESSION_KEY)
    if not isinstance(subject, str) or not subject:
        return False
    return HubIdentity.objects.filter(user=user, hub_subject=subject).exists()


class CorporateDomainPermission(BasePermission):
    """Permite acceso solo a usuarios autenticados con dominio corporativo autorizado."""

    message = "Se requiere una cuenta corporativa de un dominio autorizado."

    def has_permission(self, request, view) -> bool:
        if not getattr(settings, "CORPORATE_AUTH_REQUIRED", True):
            return True

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            self.message = "Debes iniciar sesión con una cuenta corporativa."
            return False
        if is_verified_hub_session(request, user):
            return True
        if not is_allowed_corporate_email(getattr(user, "email", "")):
            self.message = "El dominio de tu cuenta no está autorizado para esta plataforma."
            return False
        return True


class PlatformAdminPermission(BasePermission):
    """Restringe una superficie al criterio administrativo compartido."""

    message = "Se requiere el rol platform_admin para administrar esta configuración."

    def has_permission(self, request, view) -> bool:
        return is_platform_admin_user(getattr(request, "user", None))


class CanCreateBriefPermission(BasePermission):
    """Permite crear piezas a los mismos roles declarados por la capacidad del perfil."""

    message = "Tu rol corporativo no permite crear diseños."

    def has_permission(self, request, view) -> bool:
        if not getattr(settings, "CORPORATE_AUTH_REQUIRED", True):
            return True
        return can_create_briefs_user(getattr(request, "user", None))


class RolePermission(BasePermission):
    """Comprueba el grupo Django requerido por la acción del viewset."""

    message = "Tu rol corporativo no tiene permiso para esta acción."

    def has_permission(self, request, view) -> bool:
        if not getattr(settings, "CORPORATE_AUTH_REQUIRED", True):
            return True

        required_roles = getattr(view, "role_rules", {}).get(getattr(view, "action", None), ())
        if not required_roles:
            return True

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return user.groups.filter(name__in=required_roles).exists()


class RoleAwareViewSet:
    """Mixin que añade RolePermission solo a las acciones declaradas por el viewset."""

    role_rules: dict[str, tuple[str, ...]] = {}

    def get_permissions(self):
        permissions = super().get_permissions()
        if getattr(self, "action", None) in self.role_rules:
            permissions.append(RolePermission())
        return permissions
