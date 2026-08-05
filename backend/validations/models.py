from django.db import models

from designs.models import DesignVersion


class ValidationRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PASSED = "passed", "Aprobado"
        FAILED = "failed", "Fallido"

    design_version = models.ForeignKey(
        DesignVersion, on_delete=models.CASCADE, related_name="validation_runs"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    checks = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
