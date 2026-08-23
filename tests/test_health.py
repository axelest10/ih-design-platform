import json

import pytest
from django.conf import settings
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_reports_the_running_railway_release(settings):
    settings.DEPLOYMENT_COMMIT_SHA = "a" * 40
    settings.DEPLOYMENT_GIT_BRANCH = "main"
    settings.DEPLOYMENT_ENVIRONMENT = "staging"
    settings.DEPLOYMENT_SERVICE = "web"

    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ih-design-platform",
        "release": {
            "commit_sha": "a" * 40,
            "git_branch": "main",
            "environment": "staging",
            "service": "web",
        },
    }


@pytest.mark.django_db
def test_health_endpoint_marks_missing_release_metadata_without_guessing(settings):
    settings.DEPLOYMENT_COMMIT_SHA = ""
    settings.DEPLOYMENT_GIT_BRANCH = ""
    settings.DEPLOYMENT_ENVIRONMENT = "local"
    settings.DEPLOYMENT_SERVICE = ""

    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json()["release"] == {
        "commit_sha": None,
        "git_branch": None,
        "environment": "local",
        "service": None,
    }


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


def test_railway_worker_config_uses_celery_without_http_healthcheck():
    worker_config = json.loads(
        (settings.BASE_DIR / "railway.worker.json").read_text(encoding="utf-8")
    )

    assert worker_config["build"] == {
        "builder": "DOCKERFILE",
        "dockerfilePath": "/infrastructure/Dockerfile",
    }
    assert worker_config["deploy"]["startCommand"] == (
        "celery -A config worker -l info --concurrency=2"
    )
    assert "healthcheckPath" not in worker_config["deploy"]
    assert "preDeployCommand" not in worker_config["deploy"]
