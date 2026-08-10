import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from security.throttles import LoginIPThrottle


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
