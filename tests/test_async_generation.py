from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from designs.models import AsyncGenerationJob


@pytest.mark.django_db
def test_quick_design_returns_processing_job_when_worker_is_not_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = False
    client = APIClient()
    payload = {
        "template_key": "square-v1",
        "country": "MX",
        "product_slug": "general-english",
        "brand_logo_key": "ih-mexico-classic-png",
        "additional_logo_keys": [],
        "headline": "Inglés para ti",
        "body": "Aprende cerca de ti.",
    }

    with patch("materials.views.generate_quick_design_task.apply_async"):
        response = client.post("/api/v1/materials/quick-design/", payload, format="json")

    assert response.status_code == 202, response.json()
    body = response.json()
    assert body["status"] == "processing"
    assert body["status_url"].endswith(f"/api/v1/tasks/{body['task_id']}/")
    job = AsyncGenerationJob.objects.get(task_id=body["task_id"])
    assert job.status == AsyncGenerationJob.Status.QUEUED

    status = client.get(f"/api/v1/tasks/{body['task_id']}/")
    assert status.status_code == 200
    assert status.json()["status"] == "queued"


@pytest.mark.django_db
def test_task_status_does_not_expose_another_users_job(settings):
    settings.CORPORATE_AUTH_REQUIRED = False
    owner = get_user_model().objects.create_user(
        username="job-owner", email="job-owner@ihmexico.com"
    )
    other_user = get_user_model().objects.create_user(
        username="job-other", email="job-other@ihmexico.com"
    )
    job = AsyncGenerationJob.objects.create(
        task_id="foreign-task",
        kind="quick-design-generation",
        owner=owner,
    )
    client = APIClient()
    client.force_authenticate(user=other_user)
    response = client.get(f"/api/v1/tasks/{job.task_id}/")
    assert response.status_code == 404
