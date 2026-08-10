from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from security.models import MagicLinkToken


class FakeEmailClient:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)
        return "email_test_123"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def fake_email_client(monkeypatch, settings):
    client = FakeEmailClient()
    settings.RESEND_API_KEY = "re_test"
    settings.RESEND_FROM_EMAIL = "International House <login@ihmexico.com>"
    settings.MAGIC_LINK_MAX_AGE_SECONDS = 900
    monkeypatch.setattr("security.views.get_email_client", lambda: client)
    return client


def _token_from_message(message):
    verification_url = message.text.rsplit("\n", 1)[-1]
    return parse_qs(urlparse(verification_url).query)["token"][0]


@pytest.mark.django_db
def test_magic_link_request_sends_expected_email_without_user_lookup(fake_email_client):
    response = APIClient().post(
        "/api/v1/auth/magic-link/request/",
        {"email": "Persona@ihmexico.com"},
        format="json",
    )

    assert response.status_code == 202
    assert get_user_model().objects.count() == 0
    assert MagicLinkToken.objects.count() == 1
    message = fake_email_client.messages[0]
    assert message.sender == "International House <login@ihmexico.com>"
    assert message.recipients == ("persona@ihmexico.com",)
    assert message.subject == "Tu enlace de acceso a IH Design Platform"
    assert "/verify.html?token=" in message.html


@pytest.mark.django_db
def test_magic_link_request_rejects_publicly_unauthorized_domain(fake_email_client):
    response = APIClient().post(
        "/api/v1/auth/magic-link/request/",
        {"email": "persona@gmail.com"},
        format="json",
    )

    assert response.status_code == 400
    assert fake_email_client.messages == []
    assert MagicLinkToken.objects.count() == 0


@pytest.mark.django_db
def test_magic_link_request_is_throttled_by_ip(fake_email_client):
    client = APIClient()
    for attempt in range(5):
        response = client.post(
            "/api/v1/auth/magic-link/request/",
            {"email": f"persona{attempt}@ihmexico.com"},
            format="json",
            REMOTE_ADDR="198.51.100.10",
        )
        assert response.status_code == 202

    throttled = client.post(
        "/api/v1/auth/magic-link/request/",
        {"email": "persona5@ihmexico.com"},
        format="json",
        REMOTE_ADDR="198.51.100.10",
    )

    assert throttled.status_code == 429


@pytest.mark.django_db
def test_magic_link_request_is_throttled_by_email_across_ips(fake_email_client):
    client = APIClient()
    for attempt in range(3):
        response = client.post(
            "/api/v1/auth/magic-link/request/",
            {"email": "Persona@ihmexico.com"},
            format="json",
            REMOTE_ADDR=f"198.51.100.{attempt + 20}",
        )
        assert response.status_code == 202

    throttled = client.post(
        "/api/v1/auth/magic-link/request/",
        {"email": " persona@IHMEXICO.COM "},
        format="json",
        REMOTE_ADDR="198.51.100.23",
    )

    assert throttled.status_code == 429


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_magic_link_verification_creates_user_and_session(fake_email_client):
    client = APIClient()
    client.post(
        "/api/v1/auth/magic-link/request/",
        {"email": "persona@ihbogota.com"},
        format="json",
    )
    token = _token_from_message(fake_email_client.messages[0])

    verified = client.get("/api/v1/auth/magic-link/verify/", {"token": token})

    assert verified.status_code == 200
    assert verified.json() == {"authenticated": True, "email": "persona@ihbogota.com"}
    user = get_user_model().objects.get(email="persona@ihbogota.com")
    assert not user.has_usable_password()
    assert MagicLinkToken.objects.get().used_at is not None
    session = client.get("/api/v1/me/")
    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert session.json()["email"] == "persona@ihbogota.com"


@pytest.mark.django_db
def test_magic_link_is_single_use(fake_email_client):
    client = APIClient()
    client.post(
        "/api/v1/auth/magic-link/request/",
        {"email": "persona@ihlima.com"},
        format="json",
    )
    token = _token_from_message(fake_email_client.messages[0])

    assert client.get("/api/v1/auth/magic-link/verify/", {"token": token}).status_code == 200
    reused = APIClient().get("/api/v1/auth/magic-link/verify/", {"token": token})

    assert reused.status_code == 400
    assert "utilizado" in reused.json()["detail"]


@pytest.mark.django_db
def test_expired_or_tampered_magic_link_does_not_create_session(fake_email_client):
    client = APIClient()
    client.post(
        "/api/v1/auth/magic-link/request/",
        {"email": "persona@ihsantiago.cl"},
        format="json",
    )
    token = _token_from_message(fake_email_client.messages[0])
    record = MagicLinkToken.objects.get()
    record.expires_at = timezone.now()
    record.save(update_fields=["expires_at"])

    expired = client.get("/api/v1/auth/magic-link/verify/", {"token": token})
    tampered = client.get("/api/v1/auth/magic-link/verify/", {"token": f"{token}x"})

    assert expired.status_code == 400
    assert "expiró" in expired.json()["detail"]
    assert tampered.status_code == 400
    assert "válido" in tampered.json()["detail"]
    assert get_user_model().objects.count() == 0
