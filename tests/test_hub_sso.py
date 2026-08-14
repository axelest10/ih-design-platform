import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from authlib.integrations.base_client import OAuthError
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from joserfc import jwt
from joserfc.jwk import OctKey, RSAKey

from security.models import HubIdentity, HubIdentityEvent
from security.oidc import _registered_hub_client, get_hub_oidc_client
from security.services.hub_identity import (
    HubIdentityConflict,
    InactiveDesignUser,
    InvalidHubClaims,
    resolve_hub_identity,
)
from security.session_contract import (
    AUTH_METHOD_SESSION_KEY,
    HUB_AUTH_METHOD,
    HUB_SUBJECT_SESSION_KEY,
    LEGACY_PASSWORD_AUTH_METHOD,
)

CALLBACK_PATH = "/api/v1/auth/hub/callback/"
LOGIN_PATH = "/api/v1/auth/hub/login/"


@pytest.fixture
def hub_settings(settings):
    settings.HUB_OIDC_ENABLED = True
    settings.HUB_OIDC_ISSUER = "https://hub.example.test/oidc"
    settings.HUB_OIDC_CLIENT_ID = "ih-design-platform-staging"
    settings.HUB_OIDC_CLIENT_SECRET = "synthetic-client-secret-with-more-than-32-characters"
    settings.HUB_OIDC_REDIRECT_URI = "https://design.example.test/api/v1/auth/hub/callback/"
    settings.HUB_OIDC_SESSION_MAX_AGE_SECONDS = 900
    settings.HUB_OIDC_STATE_MAX_AGE_SECONDS = 600
    settings.HUB_OIDC_CLOCK_SKEW_SECONDS = 30
    _registered_hub_client.cache_clear()
    yield settings
    _registered_hub_client.cache_clear()


class FakeHubClient:
    def __init__(self, claims=None, error=None):
        self.claims = claims or {}
        self.error = error
        self.redirect_uri = None
        self.callback_kwargs = None

    def authorize_redirect(self, request, redirect_uri=None, **kwargs):
        self.redirect_uri = redirect_uri
        request.session["_state_hub_synthetic-state"] = {
            "data": {"nonce": "synthetic-nonce", "code_verifier": "synthetic-verifier"},
            "exp": time.time() + 600,
        }
        return HttpResponseRedirect(
            "https://hub.example.test/oidc/auth?state=synthetic-state&code_challenge_method=S256"
        )

    def authorize_access_token(self, request, **kwargs):
        self.callback_kwargs = kwargs
        request.session.pop(f"_state_hub_{request.GET.get('state')}", None)
        if self.error:
            raise self.error
        return {
            "access_token": "must-not-persist-access-token",
            "id_token": "must-not-persist-id-token",
            "userinfo": self.claims,
        }


def _claims(subject="hub-subject-1", email="person@example.com", name="Person"):
    return {
        "sub": subject,
        "email": email,
        "email_verified": True,
        "name": name,
    }


def _prepare_callback_session(client, next_path="/panel.html", state="synthetic-state"):
    session = client.session
    session[f"_state_hub_{state}"] = {
        "data": {"nonce": "synthetic-nonce", "code_verifier": "synthetic-verifier"},
        "exp": time.time() + 600,
    }
    session["ih_design_hub_next"] = next_path
    session.save()


@pytest.mark.django_db
def test_hub_routes_are_not_exposed_when_disabled(client, settings):
    settings.HUB_OIDC_ENABLED = False
    assert client.get(LOGIN_PATH).status_code == 404
    assert client.get(CALLBACK_PATH).status_code == 404


@pytest.mark.django_db
def test_login_uses_exact_callback_pkce_client_and_safe_relative_next(
    client, hub_settings, monkeypatch
):
    fake = FakeHubClient()
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)

    response = client.get(f"{LOGIN_PATH}?next=%2Freview.html%3Fdesign%3D42")

    assert response.status_code == 302
    assert response["Location"].startswith("https://hub.example.test/oidc/auth?")
    assert "code_challenge_method=S256" in response["Location"]
    assert fake.redirect_uri == hub_settings.HUB_OIDC_REDIRECT_URI
    assert client.session["ih_design_hub_next"] == "/review.html?design=42"
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "unsafe_next",
    [
        "https://attacker.example/path",
        "//attacker.example/path",
        "/\\attacker.example/path",
        "javascript:alert(1)",
    ],
)
def test_login_rejects_external_or_ambiguous_next_paths(
    client, hub_settings, monkeypatch, unsafe_next
):
    fake = FakeHubClient()
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)

    response = client.get(LOGIN_PATH, {"next": unsafe_next})

    assert response.status_code == 302
    assert client.session["ih_design_hub_next"] == "/panel.html"


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_callback_provisions_external_email_as_viewer_and_creates_short_session(
    client, hub_settings, monkeypatch
):
    fake = FakeHubClient(_claims())
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)
    _prepare_callback_session(client, "/review.html?design=42")

    response = client.get(CALLBACK_PATH, {"code": "synthetic-code", "state": "synthetic-state"})

    assert response.status_code == 302
    assert response["Location"] == "/review.html?design=42"
    identity = HubIdentity.objects.select_related("user").get(hub_subject="hub-subject-1")
    user = identity.user
    assert user.email == "person@example.com"
    assert not user.has_usable_password()
    assert set(user.groups.values_list("name", flat=True)) == {"viewer"}
    assert client.session[AUTH_METHOD_SESSION_KEY] == HUB_AUTH_METHOD
    assert client.session[HUB_SUBJECT_SESSION_KEY] == "hub-subject-1"
    assert client.session.get_expiry_age() <= 900
    assert "must-not-persist" not in json.dumps(dict(client.session))
    assert fake.callback_kwargs["leeway"] == 30
    assert fake.callback_kwargs["timeout"] == 10

    current_user = client.get("/api/v1/me/")
    assert current_user.status_code == 200
    assert current_user.json()["authentication_method"] == HUB_AUTH_METHOD


@pytest.mark.django_db
def test_first_link_by_email_preserves_existing_design_roles_and_password(
    client, hub_settings, monkeypatch
):
    user = get_user_model().objects.create_user(
        username="existing-designer",
        email="designer@ihmexico.com",
        password="safe-password-123",
    )
    roles = [
        Group.objects.get_or_create(name="designer")[0],
        Group.objects.get_or_create(name="reviewer")[0],
    ]
    user.groups.add(*roles)
    fake = FakeHubClient(_claims("stable-hub-sub", "designer@ihmexico.com", "Designer"))
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)
    _prepare_callback_session(client)

    response = client.get(CALLBACK_PATH, {"code": "synthetic-code", "state": "synthetic-state"})

    assert response.status_code == 302
    identity = HubIdentity.objects.get(hub_subject="stable-hub-sub")
    assert identity.user_id == user.pk
    user.refresh_from_db()
    assert user.check_password("safe-password-123")
    assert set(user.groups.values_list("name", flat=True)) == {"designer", "reviewer"}
    assert list(
        HubIdentityEvent.objects.filter(user=user).values_list("event_type", flat=True)
    ) == ["login_success", "linked"]


@pytest.mark.django_db
def test_subject_remains_primary_when_hub_email_changes_and_roles_remain_local():
    user = get_user_model().objects.create_user(
        username="linked-user",
        email="old@ihmexico.com",
        password="safe-password-123",
    )
    reviewer = Group.objects.get_or_create(name="reviewer")[0]
    user.groups.add(reviewer)
    first = resolve_hub_identity(_claims("stable-subject", "old@ihmexico.com"))

    second = resolve_hub_identity(_claims("stable-subject", "new@example.com"))

    assert first.user.pk == second.user.pk == user.pk
    user.refresh_from_db()
    assert user.email == "new@example.com"
    assert set(user.groups.values_list("name", flat=True)) == {"reviewer"}
    assert HubIdentity.objects.get(user=user).email_snapshot == "new@example.com"


@pytest.mark.django_db
def test_ambiguous_email_and_conflicting_subject_links_fail_closed():
    user_model = get_user_model()
    user_model.objects.create_user(username="duplicate-one", email="duplicate@ihmexico.com")
    user_model.objects.create_user(username="duplicate-two", email="DUPLICATE@ihmexico.com")

    with pytest.raises(HubIdentityConflict):
        resolve_hub_identity(_claims("ambiguous-subject", "duplicate@ihmexico.com"))
    assert not HubIdentity.objects.filter(hub_subject="ambiguous-subject").exists()
    assert HubIdentityEvent.objects.filter(
        event_type="login_denied", reason="identity_conflict"
    ).exists()

    linked_user = user_model.objects.create_user(username="linked", email="linked@ihmexico.com")
    resolve_hub_identity(_claims("first-subject", "linked@ihmexico.com"))
    with pytest.raises(HubIdentityConflict):
        resolve_hub_identity(_claims("second-subject", "linked@ihmexico.com"))
    assert HubIdentity.objects.get(user=linked_user).hub_subject == "first-subject"


@pytest.mark.django_db
def test_inactive_local_user_and_invalid_claims_are_denied():
    get_user_model().objects.create_user(
        username="inactive",
        email="inactive@ihmexico.com",
        is_active=False,
    )
    with pytest.raises(InactiveDesignUser):
        resolve_hub_identity(_claims("inactive-subject", "inactive@ihmexico.com"))
    with pytest.raises(InvalidHubClaims):
        resolve_hub_identity({**_claims("unverified"), "email_verified": False})
    with pytest.raises(InvalidHubClaims):
        resolve_hub_identity({**_claims("role-bearing"), "roles": ["platform_admin"]})

    assert not HubIdentity.objects.filter(
        hub_subject__in=["inactive-subject", "unverified", "role-bearing"]
    ).exists()


@pytest.mark.django_db
def test_callback_rejects_missing_expired_or_replayed_state(client, hub_settings, monkeypatch):
    fake = FakeHubClient(_claims())
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)

    missing = client.get(CALLBACK_PATH, {"code": "synthetic-code", "state": "missing"})
    _prepare_callback_session(client, state="expired")
    session = client.session
    session["_state_hub_expired"] = {"data": {}, "exp": time.time() - 1}
    session.save()
    expired = client.get(CALLBACK_PATH, {"code": "synthetic-code", "state": "expired"})

    assert missing.status_code == expired.status_code == 302
    assert missing["Location"] == expired["Location"] == "/login.html?sso_error=1"
    assert HubIdentity.objects.count() == 0

    _prepare_callback_session(client, state="single-use")
    first = client.get(CALLBACK_PATH, {"code": "first-code", "state": "single-use"})
    replay = client.get(CALLBACK_PATH, {"code": "second-code", "state": "single-use"})
    assert first.status_code == replay.status_code == 302
    assert first["Location"] == "/panel.html"
    assert replay["Location"] == "/login.html?sso_error=1"
    assert HubIdentity.objects.count() == 1


@pytest.mark.django_db
def test_provider_error_is_generic_and_does_not_create_a_session(client, hub_settings, monkeypatch):
    fake = FakeHubClient(error=OAuthError(error="invalid_grant", description="secret detail"))
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)
    _prepare_callback_session(client)

    response = client.get(CALLBACK_PATH, {"code": "bad-code", "state": "synthetic-state"})

    assert response.status_code == 302
    assert response["Location"] == "/login.html?sso_error=1"
    assert "secret detail" not in response.content.decode()
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_hub_session_logout_is_local_and_legacy_login_remains_secondary(
    client, hub_settings, monkeypatch
):
    fake = FakeHubClient(_claims())
    monkeypatch.setattr("security.hub_views.get_hub_oidc_client", lambda: fake)
    _prepare_callback_session(client)
    assert (
        client.get(
            CALLBACK_PATH, {"code": "synthetic-code", "state": "synthetic-state"}
        ).status_code
        == 302
    )

    assert client.post("/api/v1/auth/logout/").status_code == 200
    assert "_auth_user_id" not in client.session

    legacy = get_user_model().objects.create_user(
        username="legacy-user",
        email="legacy-user@ihmexico.com",
        password="safe-password-123",
    )
    response = client.post(
        "/api/v1/auth/login/",
        {"username": legacy.username, "password": "safe-password-123"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert client.session[AUTH_METHOD_SESSION_KEY] == LEGACY_PASSWORD_AUTH_METHOD
    assert HUB_SUBJECT_SESSION_KEY not in client.session


@pytest.mark.django_db
def test_protected_deep_link_redirects_to_hub_and_public_catalog_stays_public(client, hub_settings):
    protected = client.get("/review.html?design=42")
    public = client.get("/catalog.html")

    assert protected.status_code == 302
    parsed = urlparse(protected["Location"])
    assert parsed.path == LOGIN_PATH
    assert parse_qs(parsed.query) == {"next": ["/review.html?design=42"]}
    assert public.status_code == 200


def test_authlib_client_is_pinned_to_discovery_pkce_rs256_and_confidential_auth(hub_settings):
    oidc_client = get_hub_oidc_client()

    assert oidc_client._server_metadata_url == (
        "https://hub.example.test/oidc/.well-known/openid-configuration"
    )
    assert oidc_client.client_kwargs == {
        "scope": "openid profile email",
        "code_challenge_method": "S256",
        "token_endpoint_auth_method": "client_secret_basic",
        "id_token_signed_response_alg": "RS256",
        "default_timeout": 10,
    }
    assert oidc_client.framework.expires_in == 600


def test_authlib_validates_signature_issuer_audience_nonce_expiry_and_verified_email(
    hub_settings,
):
    oidc_client = get_hub_oidc_client()
    signing_key = RSAKey.import_key(
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        {"alg": "RS256", "kid": "trusted-key", "use": "sig"},
    )
    oidc_client.server_metadata = {
        "_loaded_at": time.time(),
        "issuer": hub_settings.HUB_OIDC_ISSUER,
        "id_token_signing_alg_values_supported": ["RS256"],
        "jwks": {"keys": [signing_key.as_dict(private=False)]},
    }
    now = int(time.time())
    base_claims = {
        "iss": hub_settings.HUB_OIDC_ISSUER,
        "aud": hub_settings.HUB_OIDC_CLIENT_ID,
        "sub": "synthetic-subject",
        "email": "person@example.com",
        "email_verified": True,
        "iat": now,
        "exp": now + 300,
        "nonce": "expected-nonce",
    }
    claim_rules = {
        "iss": {"essential": True, "value": hub_settings.HUB_OIDC_ISSUER},
        "aud": {"essential": True, "value": hub_settings.HUB_OIDC_CLIENT_ID},
        "email": {"essential": True},
        "email_verified": {"essential": True, "value": True},
    }

    def encoded(claims, key=signing_key):
        return jwt.encode({"alg": "RS256", "kid": "trusted-key"}, claims, key)

    valid = oidc_client.parse_id_token(
        {"id_token": encoded(base_claims)},
        nonce="expected-nonce",
        claims_options=claim_rules,
        leeway=0,
    )
    assert valid["sub"] == "synthetic-subject"

    attacker_key = RSAKey.import_key(
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        {"alg": "RS256", "kid": "trusted-key", "use": "sig"},
    )
    symmetric_key = OctKey.import_key(
        b"synthetic-symmetric-key-material",
        {"alg": "HS256", "kid": "trusted-key", "use": "sig"},
    )
    invalid_tokens = [
        (encoded({**base_claims, "iss": "https://attacker.example/oidc"}), "expected-nonce"),
        (encoded({**base_claims, "aud": "other-client"}), "expected-nonce"),
        (encoded({**base_claims, "exp": now - 1}), "expected-nonce"),
        (encoded({**base_claims, "email_verified": False}), "expected-nonce"),
        (encoded(base_claims), "wrong-nonce"),
        (encoded(base_claims, attacker_key), "expected-nonce"),
        (
            jwt.encode(
                {"alg": "HS256", "kid": "trusted-key"},
                base_claims,
                symmetric_key,
            ),
            "expected-nonce",
        ),
    ]
    for id_token, nonce in invalid_tokens:
        with pytest.raises(Exception):
            oidc_client.parse_id_token(
                {"id_token": id_token},
                nonce=nonce,
                claims_options=claim_rules,
                leeway=0,
            )


@pytest.mark.django_db
def test_identity_subject_and_audit_events_are_immutable():
    resolution = resolve_hub_identity(_claims())
    identity = resolution.identity
    identity.hub_subject = "changed-subject"
    with pytest.raises(ValidationError):
        identity.save()
    with pytest.raises(ValidationError):
        HubIdentity.objects.filter(pk=identity.pk).update(hub_subject="changed-again")
    with pytest.raises(ValidationError):
        HubIdentity.objects.filter(pk=identity.pk).delete()

    event = HubIdentityEvent.objects.filter(user=resolution.user).first()
    event.reason = "changed"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        HubIdentityEvent.objects.filter(pk=event.pk).update(reason="changed-again")
    with pytest.raises(ValidationError):
        HubIdentityEvent.objects.filter(pk=event.pk).delete()
