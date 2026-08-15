import pytest
from django.conf import settings
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint():
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ih-design-platform"}


def test_railway_healthcheck_hostname_is_allowed():
    assert "healthcheck.railway.app" in settings.ALLOWED_HOSTS


def test_dockerfile_uses_railway_port_and_emits_sanitized_gunicorn_logs():
    dockerfile = (settings.BASE_DIR / "infrastructure" / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "${PORT:-8000}" in dockerfile
    assert "--access-logfile -" in dockerfile
    assert "--access-logformat" in dockerfile
    assert "%(U)s" in dockerfile
    assert "%(q)s" not in dockerfile
    assert "%(r)s" not in dockerfile
    assert "%(f)s" not in dockerfile
    assert "--error-logfile -" in dockerfile
