"""Helpers para encolar generaciones y exponer su estado de forma segura."""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response

from ..models import AsyncGenerationJob


def enqueue_generation_task(
    task,
    *,
    owner=None,
    kind: str,
    resource_type: str = "",
    resource_id: str | int = "",
    args: Iterable | None = None,
    kwargs: dict | None = None,
) -> AsyncGenerationJob:
    """Crea el registro antes de publicar la tarea para que nunca haya un job huérfano."""
    task_id = str(uuid.uuid4())
    job = AsyncGenerationJob.objects.create(
        task_id=task_id,
        kind=kind,
        resource_type=resource_type,
        resource_id=str(resource_id or ""),
        owner=owner if owner and owner.is_authenticated else None,
    )
    try:
        task.apply_async(
            args=(task_id, *(args or ())),
            kwargs=kwargs or {},
            task_id=task_id,
        )
    except Exception as exc:
        job.status = AsyncGenerationJob.Status.FAILED
        job.error = str(exc)
        job.save(update_fields=["status", "error", "updated_at"])
        raise
    return job


def task_response(request, job: AsyncGenerationJob, *, success_status: int = 201) -> Response:
    """Devuelve el resultado eager en tests o la respuesta de polling en producción."""
    job.refresh_from_db()
    if settings.CELERY_TASK_ALWAYS_EAGER:
        if job.status == AsyncGenerationJob.Status.FAILED:
            return Response({"detail": job.error}, status=400)
        return Response(job.result, status=success_status)

    status_url = request.build_absolute_uri(
        reverse("generation-task-status", args=[job.task_id])
    )
    return Response(
        {
            "task_id": job.task_id,
            "status": "processing",
            "status_url": status_url,
            "kind": job.kind,
            "resource_type": job.resource_type,
            "resource_id": job.resource_id or None,
        },
        status=202,
    )
