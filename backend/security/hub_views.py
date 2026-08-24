from __future__ import annotations

import time
from collections.abc import Mapping
from urllib.parse import urlsplit

from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import Http404, HttpResponseRedirect
from django.views.decorators.http import require_GET
from requests import RequestException

from common.observability import operation_event

from .oidc import get_hub_oidc_client
from .services.hub_identity import (
    HubIdentityError,
    record_hub_identity_denial,
    resolve_hub_identity,
)
from .session_contract import (
    AUTH_METHOD_SESSION_KEY,
    HUB_AUTH_METHOD,
    HUB_SUBJECT_SESSION_KEY,
)

HUB_NEXT_SESSION_KEY = "ih_design_hub_next"
DEFAULT_NEXT_PATH = "/panel.html"


@require_GET
def hub_oidc_login(request):
    _require_hub_oidc()
    next_path = safe_local_next(request.GET.get("next"), DEFAULT_NEXT_PATH)
    if request.user.is_authenticated:
        django_logout(request)
    request.session.cycle_key()
    request.session[HUB_NEXT_SESSION_KEY] = next_path
    request.session.set_expiry(settings.HUB_OIDC_STATE_MAX_AGE_SECONDS)

    client = get_hub_oidc_client()
    response = client.authorize_redirect(
        request,
        redirect_uri=settings.HUB_OIDC_REDIRECT_URI,
    )
    response["Cache-Control"] = "no-store"
    operation_event(
        "authentication.hub_oidc.start",
        status="started",
        provider="ih_latam_hub",
        http_status=302,
    )
    return response


@require_GET
def hub_oidc_callback(request):
    _require_hub_oidc()
    try:
        _assert_fresh_state(request)
        client = get_hub_oidc_client()
        token = client.authorize_access_token(
            request,
            claims_options={
                "iss": {"essential": True, "value": settings.HUB_OIDC_ISSUER},
                "aud": {"essential": True, "value": settings.HUB_OIDC_CLIENT_ID},
                "email": {"essential": True},
                "email_verified": {"essential": True, "value": True},
            },
            leeway=settings.HUB_OIDC_CLOCK_SKEW_SECONDS,
            timeout=10,
        )
        userinfo = token.pop("userinfo", None)
        token.clear()
        if not isinstance(userinfo, Mapping):
            raise OAuthError(description="Missing validated ID token claims")

        resolution = resolve_hub_identity(userinfo)
        next_path = safe_local_next(
            request.session.pop(HUB_NEXT_SESSION_KEY, DEFAULT_NEXT_PATH),
            DEFAULT_NEXT_PATH,
        )
        django_login(
            request,
            resolution.user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        request.session[AUTH_METHOD_SESSION_KEY] = HUB_AUTH_METHOD
        request.session[HUB_SUBJECT_SESSION_KEY] = resolution.identity.hub_subject
        request.session.set_expiry(settings.HUB_OIDC_SESSION_MAX_AGE_SECONDS)
        operation_event(
            "authentication.hub_oidc.callback",
            status="success",
            provider="ih_latam_hub",
            user_id=resolution.user.pk,
            http_status=302,
        )
        response = HttpResponseRedirect(next_path)
        response["Cache-Control"] = "no-store"
        return response
    except HubIdentityError as exc:
        return _deny_callback(request, exc.reason)
    except (OAuthError, RequestException, ValueError, TypeError):
        record_hub_identity_denial("", "protocol_validation_failed")
        return _deny_callback(request, "protocol_validation_failed")
    except Exception:
        record_hub_identity_denial("", "provider_unavailable")
        return _deny_callback(request, "provider_unavailable")


def safe_local_next(value, default: str = DEFAULT_NEXT_PATH) -> str:
    candidate = str(value or "").strip()
    if not candidate or len(candidate) > 2048 or "\\" in candidate:
        return default
    parsed = urlsplit(candidate)
    if (
        parsed.scheme
        or parsed.netloc
        or not parsed.path.startswith("/")
        or parsed.path.startswith("//")
    ):
        return default
    return candidate


def _assert_fresh_state(request) -> None:
    state = str(request.GET.get("state") or "")
    key = f"_state_hub_{state}"
    state_record = request.session.get(key)
    expires_at = state_record.get("exp") if isinstance(state_record, dict) else None
    if not state or not isinstance(expires_at, (int, float)) or expires_at < time.time():
        request.session.pop(key, None)
        raise OAuthError(description="Missing, invalid, or expired state")


def _deny_callback(request, reason: str):
    request.session.pop(HUB_NEXT_SESSION_KEY, None)
    operation_event(
        "authentication.hub_oidc.callback",
        status="failed",
        provider="ih_latam_hub",
        reason=reason,
        http_status=302,
    )
    response = HttpResponseRedirect("/login.html?sso_error=1")
    response["Cache-Control"] = "no-store"
    return response


def _require_hub_oidc() -> None:
    if not settings.HUB_OIDC_ENABLED:
        raise Http404("Hub OIDC is not enabled")
