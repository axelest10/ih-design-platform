import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from security.permissions import CORPORATE_ROLES
from security.throttles import SiteAccessIPThrottle
from security.views import SHARED_ACCESS_USERNAME


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_correct_site_password_creates_full_access_session(settings):
    settings.SITE_ACCESS_PASSWORD = "shared-secret"
    client = APIClient()

    response = client.post(
        "/api/v1/auth/site-access/",
        {"password": "shared-secret"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    current_user = client.get("/api/v1/me/")
    assert current_user.status_code == 200
    assert current_user.json()["is_admin"] is True
    assert set(current_user.json()["roles"]) == set(CORPORATE_ROLES)

    shared_user = get_user_model().objects.get(username=SHARED_ACCESS_USERNAME)
    assert shared_user.email == "acceso@ihmexico.com"
    assert not shared_user.has_usable_password()


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_incorrect_site_password_does_not_create_session(settings):
    settings.SITE_ACCESS_PASSWORD = "shared-secret"
    client = APIClient()

    response = client.post(
        "/api/v1/auth/site-access/",
        {"password": "incorrect"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "No fue posible iniciar sesión."}
    assert "_auth_user_id" not in client.session
    assert client.get("/api/v1/me/").status_code == 403


@pytest.mark.django_db
def test_site_access_returns_503_when_password_is_not_configured(settings):
    settings.SITE_ACCESS_PASSWORD = ""

    response = APIClient().post(
        "/api/v1/auth/site-access/",
        {"password": "anything"},
        format="json",
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "El acceso interno no está configurado."}


@pytest.mark.django_db
def test_site_access_is_throttled_by_ip(settings, monkeypatch):
    settings.SITE_ACCESS_PASSWORD = "shared-secret"
    monkeypatch.setattr(SiteAccessIPThrottle, "rate", "2/hour", raising=False)
    client = APIClient()

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/site-access/",
            {"password": "incorrect"},
            format="json",
            REMOTE_ADDR="198.51.100.10",
        )
        assert response.status_code == 401

    throttled = client.post(
        "/api/v1/auth/site-access/",
        {"password": "incorrect"},
        format="json",
        REMOTE_ADDR="198.51.100.10",
    )

    assert throttled.status_code == 429
