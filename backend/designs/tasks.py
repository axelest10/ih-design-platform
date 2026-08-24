"""Tareas Celery para generaciones que no deben ejecutarse dentro de una vista."""
from __future__ import annotations

import json
from html import escape

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from briefs.models import DesignBrief
from briefs.services.design_confirmation import confirm_brief_design
from designs.models import AsyncGenerationJob, Design, DesignDelivery, DesignVersion
from designs.services.renderer_document import render_document_preview
from designs.services.renderer_presentation import render_presentation_preview
from designs.services.revision import revise_design
from designs.services.storage_paths import generated_design_path
from materials.models import MaterialBundle, MaterialType
from materials.services.quick_design import create_quick_design
from materials.services.school_kit import generate_school_kit
from security.models import EmailRecipientState, TransactionalEmailDelivery
from security.services.email import (
    EmailDeliveryError,
    EmailDeliverySuppressed,
    send_transactional_email,
)


def _generation_storage():
    """Resolve the configured storage at execution time for worker and eager runs."""
    from designs.views import default_storage as configured_storage

    return configured_storage


def _run_job(job_id: str, callback):
    AsyncGenerationJob.objects.filter(task_id=job_id).update(
        status=AsyncGenerationJob.Status.PROCESSING,
        error="",
    )
    try:
        result = callback()
    except Exception as exc:
        AsyncGenerationJob.objects.filter(task_id=job_id).update(
            status=AsyncGenerationJob.Status.FAILED,
            error=str(exc),
        )
        raise
    serializable_result = json.loads(json.dumps(result, cls=DjangoJSONEncoder))
    AsyncGenerationJob.objects.filter(task_id=job_id).update(
        status=AsyncGenerationJob.Status.SUCCEEDED,
        result=serializable_result,
    )
    return serializable_result


def _design_state_after_generation(design: Design) -> None:
    update_fields = ["status", "updated_at"]
    if design.brief.product_slug and settings.DESIGN_TEST_MODE:
        if design.test_number is None:
            latest_test = (
                Design.objects.filter(test_number__isnull=False).aggregate(
                    max_number=Max("test_number")
                )["max_number"]
                or 0
            )
            design.test_number = latest_test + 1
            update_fields.append("test_number")
        design.status = Design.Status.SELF_REVIEW
    else:
        design.status = Design.Status.IN_REVIEW
    design.save(update_fields=update_fields)


def _store_binary_version(design: Design, rendered, *, extension: str, data_key: str):
    storage = _generation_storage()
    with transaction.atomic():
        next_number = (
            design.versions.aggregate(max_number=Max("number"))["max_number"] or 0
        ) + 1
        path = storage.save(
            generated_design_path(design, f"version-{next_number}.{extension}"),
            ContentFile(getattr(rendered, extension)),
        )
        version = DesignVersion.objects.create(
            design=design,
            number=next_number,
            template_key=rendered.template_key,
            render_data={**rendered.data, data_key: path},
            asset_refs=[*rendered.asset_refs, path],
            validation_summary=rendered.validation_summary,
        )
        _design_state_after_generation(design)
    return version, path


def _binary_result(design: Design, version: DesignVersion, rendered, path: str, *, key: str):
    storage = _generation_storage()
    from ai.services import run_automatic_design_review

    run_automatic_design_review(version)
    design.refresh_from_db(fields=["status", "updated_at", "test_number"])
    return {
        "design_id": str(design.pk),
        "status": design.status,
        "version": version.number,
        "test_number": design.test_number,
        "template_key": rendered.template_key,
        "template_version": rendered.template_version,
        "validation": rendered.validation_summary,
        "test_batch_limit": settings.DESIGN_TEST_LIMIT,
        "test_batch_complete": bool(
            design.test_number and design.test_number >= settings.DESIGN_TEST_LIMIT
        ),
        "preview": {f"{key}_url": storage.url(path)},
    }


@shared_task(name="designs.generate_document_preview")
def generate_document_preview_task(job_id, design_id, render_payload, material_type_id):
    def run():
        design = Design.objects.select_related("brief").get(pk=design_id)
        material_type = MaterialType.objects.get(pk=material_type_id)
        rendered = render_document_preview(render_payload, material_type=material_type)
        version, path = _store_binary_version(
            design, rendered, extension="pdf", data_key="pdf_path"
        )
        return _binary_result(design, version, rendered, path, key="pdf")

    return _run_job(job_id, run)


@shared_task(name="designs.generate_presentation_preview")
def generate_presentation_preview_task(job_id, design_id, render_payload, material_type_id):
    def run():
        design = Design.objects.select_related("brief").get(pk=design_id)
        material_type = MaterialType.objects.get(pk=material_type_id)
        rendered = render_presentation_preview(render_payload, material_type=material_type)
        version, path = _store_binary_version(
            design, rendered, extension="pptx", data_key="pptx_path"
        )
        return _binary_result(design, version, rendered, path, key="pptx")

    return _run_job(job_id, run)


@shared_task(name="materials.generate_quick_design")
def generate_quick_design_task(job_id, payload, user_id=None):
    def run():
        user = None
        if user_id:
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.filter(pk=user_id).first()
        return create_quick_design(payload, user=user)

    return _run_job(job_id, run)


@shared_task(name="materials.generate_school_kit")
def generate_school_kit_task(job_id, bundle_id, user_id=None):
    def run():
        bundle = MaterialBundle.objects.get(pk=bundle_id)
        user = None
        if user_id:
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.filter(pk=user_id).first()
        generate_school_kit(bundle, user=user)
        from materials.serializers import MaterialBundleSerializer

        bundle.refresh_from_db()
        return MaterialBundleSerializer(bundle).data

    return _run_job(job_id, run)


@shared_task(name="briefs.confirm_design")
def confirm_brief_design_task(job_id, brief_id, prompt_text):
    def run():
        brief = DesignBrief.objects.get(pk=brief_id)
        design = confirm_brief_design(brief, prompt_text)
        from designs.serializers import DesignSerializer

        return DesignSerializer(design).data

    return _run_job(job_id, run)


@shared_task(name="designs.revise_design")
def revise_design_task(job_id, design_id, instruction):
    def run():
        design = Design.objects.get(pk=design_id)
        design = revise_design(design, instruction)
        from designs.serializers import DesignSerializer

        return DesignSerializer(design).data

    return _run_job(job_id, run)


@shared_task(name="designs.deliver_approved_design")
def deliver_approved_design_task(delivery_id):
    """EnvÃ­a al solicitante un link de descarga de la versiÃ³n aprobada."""
    delivery = DesignDelivery.objects.select_related(
        "design__brief", "version", "requested_by"
    ).get(pk=delivery_id)
    if delivery.status == DesignDelivery.Status.DELIVERED:
        return {"delivery_id": delivery.pk, "status": delivery.status}
    if not delivery.recipient_email:
        delivery.status = DesignDelivery.Status.NO_RECIPIENT
        delivery.error = "El brief aprobado no tiene un solicitante con email."
        delivery.save(update_fields=["status", "error", "updated_at"])
        return {"delivery_id": delivery.pk, "status": delivery.status}

    delivery.status = DesignDelivery.Status.PROCESSING
    delivery.error = ""
    delivery.save(update_fields=["status", "error", "updated_at"])
    title = delivery.design.brief.title
    subject = f"Tu diseño aprobado: {title}"
    link = delivery.download_url
    email_delivery = TransactionalEmailDelivery.objects.create(
        recipient=delivery.recipient_email.strip().casefold(),
        user=delivery.requested_by,
        message_stream=settings.POSTMARK_MESSAGE_STREAM,
        tag="approved-design",
    )
    try:
        provider_message_id = send_transactional_email(
            to=delivery.recipient_email,
            subject=subject,
            html_body=(
                f"<p>Tu diseño <strong>{escape(title)}</strong> fue aprobado.</p>"
                f"<p><a href=\"{escape(link, quote=True)}\">Descargar diseño aprobado</a></p>"
                "<p>El enlace requiere iniciar sesión en IH Design Platform.</p>"
            ),
            text_body=(
                f"Tu diseño '{title}' fue aprobado. Descárgalo aquí: {link}\n\n"
                "El enlace requiere iniciar sesión en IH Design Platform."
            ),
            tag="approved-design",
            metadata={
                "email_delivery_id": str(email_delivery.pk),
                "design_delivery_id": str(delivery.pk),
            },
        )
    except EmailDeliverySuppressed as exc:
        email_delivery.refresh_from_db()
        if email_delivery.last_event_at is None:
            email_delivery.status = TransactionalEmailDelivery.Status.SUPPRESSED
            email_delivery.failure_category = exc.category
            email_delivery.suppressed = exc.category == "recipient_provider_suppressed"
        email_delivery.save()
        delivery.status = DesignDelivery.Status.FAILED
        delivery.error = str(exc)
        delivery.save(update_fields=["status", "error", "updated_at"])
        return {"delivery_id": delivery.pk, "status": delivery.status, "error": str(exc)}
    except EmailDeliveryError as exc:
        email_delivery.refresh_from_db()
        if email_delivery.last_event_at is None:
            email_delivery.status = TransactionalEmailDelivery.Status.FAILED
            email_delivery.failure_category = exc.category
        email_delivery.save()
        delivery.status = DesignDelivery.Status.FAILED
        delivery.error = str(exc)
        delivery.save(update_fields=["status", "error", "updated_at"])
        return {"delivery_id": delivery.pk, "status": delivery.status, "error": str(exc)}

    email_delivery.refresh_from_db()
    email_delivery.provider_message_id = provider_message_id
    email_delivery.accepted_at = timezone.now()
    if email_delivery.last_event_at is None:
        email_delivery.status = TransactionalEmailDelivery.Status.ACCEPTED
    email_delivery.save()
    EmailRecipientState.objects.get_or_create(recipient=email_delivery.recipient)
    delivery.status = DesignDelivery.Status.DELIVERED
    delivery.provider_message_id = provider_message_id
    delivery.delivered_at = timezone.now()
    delivery.save(
        update_fields=["status", "provider_message_id", "delivered_at", "updated_at"]
    )
    return {
        "delivery_id": delivery.pk,
        "status": delivery.status,
        "provider_message_id": provider_message_id,
    }
