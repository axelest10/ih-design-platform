from django.db import models


class AICallAudit(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completada"
        ERROR = "error", "Error"

    provider = models.CharField(max_length=80)
    model = models.CharField(max_length=160, blank=True)
    prompt = models.TextField()
    response = models.TextField(blank=True)
    request_context = models.JSONField(default=dict)
    response_metadata = models.JSONField(default=dict)
    quality_report = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.COMPLETED)
    brief = models.ForeignKey(
        "briefs.DesignBrief",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_call_audits",
    )
    design_version = models.ForeignKey(
        "designs.DesignVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_call_audits",
    )
    material_bundle = models.ForeignKey(
        "materials.MaterialBundle",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_call_audits",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
