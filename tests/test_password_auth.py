import logging
from pathlib import Path
from urllib.parse import unquote

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.middleware.csrf import get_token
from django.test import RequestFactory, override_settings
from rest_framework.test import APIClient

from security.models import PasswordResetToken, TransactionalEmailDelivery
from security.throttles import LoginIPThrottle

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_individual_login_creates_session_for_corporate_user():
    user = get_user_model().objects.create_user(
        username="persona",
        email="persona@ihmexico.com",
        password="safe-password-123",
    )
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"username": "persona", "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": "persona"}
    current_user = client.get("/api/v1/me/")
    assert current_user.status_code == 200
    assert current_user.json()["email"] == user.email


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_authenticated_user_can_submit_login_again_without_csrf_error():
    user = get_user_model().objects.create_user(
        username="persona",
        email="persona@ihmexico.com",
        password="safe-password-123",
    )
    client = APIClient(enforce_csrf_checks=True)
    assert client.login(username=user.username, password="safe-password-123")

    response = client.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "username": user.username}


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_authenticated_user_can_log_out_with_csrf_and_session_is_removed():
    user = get_user_model().objects.create_user(
        username="logout-person",
        email="logout-person@ihmexico.com",
        password="safe-password-123",
    )
    client = APIClient(enforce_csrf_checks=True)
    assert client.login(username=user.username, password="safe-password-123")
    request = RequestFactory().get("/")
    token = get_token(request)
    client.cookies["csrftoken"] = request.META["CSRF_COOKIE"]

    rejected = client.post("/api/v1/auth/logout/")
    assert rejected.status_code == 403

    response = client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=token)

    assert response.status_code == 200
    assert response.json() == {"authenticated": False}
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"username": "unknown", "password": "safe-password-123"},
        {"username": "persona", "password": "wrong-password"},
    ],
)
def test_invalid_credentials_return_same_generic_error(payload):
    get_user_model().objects.create_user(
        username="persona",
        email="persona@ihmexico.com",
        password="safe-password-123",
    )
    client = APIClient()

    response = client.post("/api/v1/auth/login/", payload, format="json")

    assert response.status_code == 401
    assert response.json() == {"detail": "Usuario o contraseña incorrectos."}
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_valid_password_with_unauthorized_domain_is_rejected():
    get_user_model().objects.create_user(
        username="external",
        email="external@example.com",
        password="safe-password-123",
    )

    response = APIClient().post(
        "/api/v1/auth/login/",
        {"username": "external", "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_inactive_account_is_rejected_without_creating_a_session():
    get_user_model().objects.create_user(
        username="inactive-person",
        email="inactive-person@ihmexico.com",
        password="safe-password-123",
        is_active=False,
    )
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"username": "inactive-person", "password": "safe-password-123"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Usuario o contraseña incorrectos."}
    assert "_auth_user_id" not in client.session


def test_default_login_throttle_remains_ten_attempts_per_hour(settings):
    assert settings.LOGIN_THROTTLE_RATE == "10/hour"


@pytest.mark.django_db
def test_login_is_throttled_by_ip(monkeypatch):
    monkeypatch.setattr(LoginIPThrottle, "rate", "2/hour", raising=False)
    client = APIClient()

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login/",
            {"username": "unknown", "password": "incorrect"},
            format="json",
            REMOTE_ADDR="198.51.100.10",
        )
        assert response.status_code == 401

    throttled = client.post(
        "/api/v1/auth/login/",
        {"username": "unknown", "password": "incorrect"},
        format="json",
        REMOTE_ADDR="198.51.100.10",
    )

    assert throttled.status_code == 429


@pytest.mark.django_db
def test_initial_admin_exists_and_shared_access_is_disabled():
    admin = get_user_model().objects.get(username="axel.estrada@ihmexico.com")
    shared = get_user_model().objects.get(username="shared-access")

    assert admin.email == "axel.estrada@ihmexico.com"
    assert admin.is_active is True
    assert admin.has_usable_password()
    assert admin.groups.filter(name="platform_admin").exists()
    assert admin.email.rsplit("@", 1)[1] in {
        "ihmexico.com",
        "ihbogota.com",
        "ihsantiago.cl",
        "ihlima.com",
    }
    assert shared.is_active is False


@pytest.mark.django_db
@override_settings(
    PASSWORD_RESET_MAX_AGE_SECONDS=900,
)
def test_password_reset_is_generic_sends_fragment_token_and_is_single_use(
    monkeypatch, caplog
):
    user = get_user_model().objects.create_user(
        username="recoverable",
        email="recoverable@ihmexico.com",
        password="old-password-123",
    )
    captured = []

    def fake_send_transactional_email(**message):
        captured.append(message)
        return "postmark-message-safe-id"

    monkeypatch.setattr(
        "security.views.send_transactional_email",
        fake_send_transactional_email,
    )
    caplog.set_level(logging.INFO, logger="ih_design.operations")
    client = APIClient()

    requested = client.post(
        "/api/v1/auth/password-reset/request/",
        {"email": user.email},
        format="json",
    )

    assert requested.status_code == 202
    assert len(captured) == 1
    assert captured[0]["to"] == user.email
    assert captured[0]["subject"] == "Recupera tu acceso a IH Design Platform"
    assert captured[0]["tag"] == "password-reset"
    assert "/login.html#reset=" in captured[0]["text_body"]
    record = PasswordResetToken.objects.get(user=user)
    delivery = TransactionalEmailDelivery.objects.get(user=user)
    assert delivery.password_reset_token == record
    assert delivery.provider_message_id == "postmark-message-safe-id"
    assert delivery.status == TransactionalEmailDelivery.Status.ACCEPTED
    assert captured[0]["metadata"] == {"email_delivery_id": str(delivery.pk)}
    assert record.token_hash not in captured[0]["text_body"]
    token = unquote(captured[0]["text_body"].split("#reset=", 1)[1].strip())
    events = [record.message for record in caplog.records if record.name == "ih_design.operations"]
    assert any("postmark-message-safe-id" in event for event in events)
    assert all(token not in event for event in events)

    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"token": token, "new_password": "new-password-456"},
        format="json",
    )
    replayed = client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"token": token, "new_password": "another-password-789"},
        format="json",
    )

    assert confirmed.status_code == 200
    assert replayed.status_code == 400
    user.refresh_from_db()
    assert user.check_password("new-password-456")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email",
    ["unknown@ihmexico.com", "person@example.com", "inactive@ihmexico.com"],
)
def test_password_reset_request_does_not_enumerate_accounts(email):
    get_user_model().objects.create_user(
        username="inactive",
        email="inactive@ihmexico.com",
        password="old-password-123",
        is_active=False,
    )

    response = APIClient().post(
        "/api/v1/auth/password-reset/request/",
        {"email": email},
        format="json",
    )

    assert response.status_code == 202
    assert response.json() == {
        "detail": "Si la cuenta puede recuperar su acceso, recibirá un correo con instrucciones."
    }
    assert PasswordResetToken.objects.count() == 0


@pytest.mark.django_db
def test_password_reset_confirm_enforces_minimum_length():
    response = APIClient().post(
        "/api/v1/auth/password-reset/confirm/",
        {"token": "not-a-token", "new_password": "short"},
        format="json",
    )

    assert response.status_code == 400
    assert "new_password" in response.json()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_user_changes_own_password_without_losing_current_session():
    user = get_user_model().objects.create_user(
        username="self-service-user",
        email="self-service@ihmexico.com",
        password="current-password-123",
    )
    client = APIClient()
    assert client.login(username=user.username, password="current-password-123")

    response = client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "current-password-123",
            "new_password": "replacement-password-456",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {"detail": "Contraseña actualizada correctamente."}
    user.refresh_from_db()
    assert user.check_password("replacement-password-456")

    current_user = client.get("/api/v1/me/")
    assert current_user.status_code == 200
    assert current_user.json()["authenticated"] is True
    assert current_user.json()["email"] == user.email


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_user_cannot_change_password_with_incorrect_current_password():
    user = get_user_model().objects.create_user(
        username="self-service-user",
        email="self-service@ihmexico.com",
        password="current-password-123",
    )
    client = APIClient()
    assert client.login(username=user.username, password="current-password-123")

    response = client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "incorrect-password",
            "new_password": "replacement-password-456",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "La contraseña actual no es correcta."}
    user.refresh_from_db()
    assert user.check_password("current-password-123")


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_change_password_requires_twelve_character_new_password():
    user = get_user_model().objects.create_user(
        username="self-service-user",
        email="self-service@ihmexico.com",
        password="current-password-123",
    )
    client = APIClient()
    assert client.login(username=user.username, password="current-password-123")

    response = client.post(
        "/api/v1/auth/change-password/",
        {"current_password": "current-password-123", "new_password": "too-short"},
        format="json",
    )

    assert response.status_code == 400
    assert "new_password" in response.json()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_change_password_requires_an_authenticated_session():
    response = APIClient().post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "current-password-123",
            "new_password": "replacement-password-456",
        },
        format="json",
    )

    assert response.status_code in {401, 403}


def test_password_forms_include_confirmation_and_shared_visibility_control():
    panel = (REPO_ROOT / "frontend" / "panel.html").read_text(encoding="utf-8")
    admin = (REPO_ROOT / "frontend" / "admin.html").read_text(encoding="utf-8")
    panel_script = (
        REPO_ROOT / "frontend" / "scripts" / "panel.js"
    ).read_text(encoding="utf-8")
    admin_script = (
        REPO_ROOT / "frontend" / "scripts" / "admin.js"
    ).read_text(encoding="utf-8")
    shared_script = (
        REPO_ROOT / "frontend" / "scripts" / "password-fields.js"
    ).read_text(encoding="utf-8")
    csrf_script = (
        REPO_ROOT / "frontend" / "scripts" / "csrf.js"
    ).read_text(encoding="utf-8")

    assert 'name="new_password_confirmation"' in panel
    assert 'name="password_confirmation"' in admin
    assert admin.count('name="password_confirmation"') == 2
    assert "data-password-toggle" in panel
    assert admin.count("data-password-toggle") == 2
    assert "asset_url 'scripts/password-fields.js'" in panel
    assert "asset_url 'scripts/password-fields.js'" in admin
    assert "IHPasswordFields.valuesMatch" in panel_script
    assert admin_script.count("IHPasswordFields.valuesMatch") == 2
    assert 'authenticatedFetch("/api/v1/auth/change-password/"' in panel_script
    assert 'headers.set("X-CSRFToken"' in csrf_script
    assert 'input.type = visible ? "text" : "password"' in shared_script


def test_login_frontend_sends_csrf_and_redirects_an_existing_session():
    login_html = (REPO_ROOT / "frontend" / "login.html").read_text(encoding="utf-8")
    login_styles = (
        REPO_ROOT / "frontend" / "styles" / "auth.css"
    ).read_text(encoding="utf-8")
    login_script = (
        REPO_ROOT / "frontend" / "scripts" / "login.js"
    ).read_text(encoding="utf-8")
    csrf_script = (
        REPO_ROOT / "frontend" / "scripts" / "csrf.js"
    ).read_text(encoding="utf-8")

    assert login_html.index("asset_url 'scripts/csrf.js'") < login_html.index(
        "asset_url 'scripts/login.js'"
    )
    assert 'window.authenticatedFetch("/api/v1/auth/login/"' in login_script
    assert 'cookie("csrftoken")' in csrf_script
    assert 'headers.set("X-CSRFToken"' in csrf_script
    assert 'fetch("/api/v1/me/")' in login_script
    assert "window.location.replace(nextPath)" in login_script
    assert 'return "/panel.html"' in login_script
    assert 'id="hub-sso-button"' in login_html
    assert "Acceso de contingencia" in login_html
    assert "password-reset/request/" in login_script
    assert "password-reset/confirm/" in login_script
    assert "#reset=" not in login_script
    assert ".auth-form[hidden] { display: none; }" in login_styles


def test_panel_exposes_logout_action_and_uses_authenticated_post():
    panel_html = (REPO_ROOT / "frontend" / "panel.html").read_text(encoding="utf-8")
    panel_script = (
        REPO_ROOT / "frontend" / "scripts" / "panel.js"
    ).read_text(encoding="utf-8")

    assert 'id="auth-action"' in panel_html
    assert 'textContent = "Cerrar sesión"' in panel_script
    assert 'authenticatedFetch("/api/v1/auth/logout/", { method: "POST" })' in panel_script
    assert 'window.location.href = "/login.html"' in panel_script
