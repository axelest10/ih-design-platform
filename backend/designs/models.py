import uuid

from django.contrib.auth import get_user_model
from django.db import models

from briefs.models import DesignBrief


class Design(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        IN_REVIEW = "in_review", "En revisión"
        APPROVED = "approved", "Aprobado"
        REJECTED = "rejected", "Rechazado"
        SELF_REVIEW = "self_review", "Revision de Claude"
        TEST_READY = "test_ready", "Listo para prueba"
        REVISION_REQUESTED = "revision_requested", "Cambios solicitados"
        ARCHIVED = "archived", "Archivado"

    brief = models.OneToOneField(DesignBrief, on_delete=models.PROTECT, related_name="design")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    approved_version = models.ForeignKey(
        "DesignVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_for",
    )
    test_number = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DesignVersion(models.Model):
    class ClaudeReviewStatus(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PASS = "pass", "Correcto"
        NEEDS_CHANGES = "needs_changes", "Requiere cambios"

    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    template_key = models.CharField(max_length=120)
    render_data = models.JSONField(default=dict)
    asset_refs = models.JSONField(default=list)
    validation_summary = models.JSONField(default=dict)
    claude_review_status = models.CharField(
        max_length=20,
        choices=ClaudeReviewStatus.choices,
        default=ClaudeReviewStatus.PENDING,
    )
    claude_review = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["design", "number"], name="unique_design_version")
        ]
        ordering = ["-number"]


class AsyncGenerationJob(models.Model):
    """Estado persistido de una generación procesada por Celery."""

    class Status(models.TextChoices):
        QUEUED = "queued", "En cola"
        PROCESSING = "processing", "Procesando"
        SUCCEEDED = "succeeded", "Completado"
        FAILED = "failed", "Fallido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=40, blank=True)
    resource_id = models.CharField(max_length=64, blank=True)
    owner = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="async_generation_jobs",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    result = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class DesignReviewComment(models.Model):
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="review_comments")
    version = models.ForeignKey(
        DesignVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="review_comments",
    )
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        related_name="design_review_comments",
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]


class DesignDelivery(models.Model):
    """Registro auditable de la entrega de una versiÃ³n aprobada al solicitante."""

    class Status(models.TextChoices):
        QUEUED = "queued", "En cola"
        PROCESSING = "processing", "Procesando"
        DELIVERED = "delivered", "Entregado"
        FAILED = "failed", "Fallido"
        NO_RECIPIENT = "no_recipient", "Sin destinatario"

    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="deliveries")
    version = models.ForeignKey(
        DesignVersion,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    requested_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="design_deliveries_requested",
    )
    recipient_email = models.EmailField(blank=True)
    channel = models.CharField(max_length=24, default="email")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    download_url = models.URLField(max_length=1000, blank=True)
    provider_message_id = models.CharField(max_length=160, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
