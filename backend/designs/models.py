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
