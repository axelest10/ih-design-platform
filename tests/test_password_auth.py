from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

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
    assert shared.is_active is False


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

    assert 'name="new_password_confirmation"' in panel
    assert 'name="password_confirmation"' in admin
    assert admin.count('name="password_confirmation"') == 2
    assert "data-password-toggle" in panel
    assert admin.count("data-password-toggle") == 2
    assert 'src="scripts/password-fields.js"' in panel
    assert 'src="scripts/password-fields.js"' in admin
    assert "IHPasswordFields.valuesMatch" in panel_script
    assert admin_script.count("IHPasswordFields.valuesMatch") == 2
    assert 'fetch("/api/v1/auth/change-password/"' in panel_script
    assert 'headers.set("X-CSRFToken"' in panel_script
    assert 'input.type = visible ? "text" : "password"' in shared_script


def test_login_frontend_sends_csrf_and_redirects_an_existing_session():
    login_script = (
        REPO_ROOT / "frontend" / "scripts" / "login.js"
    ).read_text(encoding="utf-8")

    assert 'cookie("csrftoken")' in login_script
    assert 'headers.set("X-CSRFToken"' in login_script
    assert 'request("/api/v1/me/")' in login_script
    assert 'window.location.replace("/panel.html")' in login_script
