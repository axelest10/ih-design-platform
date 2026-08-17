"""Entrega por correo de una versiÃ³n de diseÃ±o aprobada."""
from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings

from designs.models import Design, DesignDelivery, DesignVersion


def _output_for_version(version: DesignVersion) -> str:
    if version.render_data.get("pdf_path"):
        return "pdf"
    if version.render_data.get("pptx_path"):
        return "pptx"
    if version.render_data.get("svg"):
        return "svg"
    return "html"


def create_approved_design_delivery(
    *,
    design: Design,
    version: DesignVersion,
    base_url: str,
) -> DesignDelivery:
    """Registra al solicitante y encola un link autenticado de descarga."""
    requester = design.brief.created_by
    recipient_email = str(getattr(requester, "email", "") or "").strip()
    output = _output_for_version(version)
    path = f"/api/v1/designs/{design.pk}/versions/{version.number}/export/"
    download_url = f"{base_url.rstrip('/')}{path}?{urlencode({'output': output})}"
    delivery = DesignDelivery.objects.create(
        design=design,
        version=version,
        requested_by=requester,
        recipient_email=recipient_email,
        download_url=download_url,
        status=(
            DesignDelivery.Status.QUEUED
            if recipient_email
            else DesignDelivery.Status.NO_RECIPIENT
        ),
        error="" if recipient_email else "El brief aprobado no tiene un solicitante con email.",
    )
    if recipient_email:
        from designs.tasks import deliver_approved_design_task

        deliver_approved_design_task.apply_async(args=(delivery.pk,))
        if settings.CELERY_TASK_ALWAYS_EAGER:
            delivery.refresh_from_db()
    return delivery
