import uuid

from django.db import models

from campaigns.models import Campaign
from catalog.models import Branch, Product


class DesignBrief(models.Model):
    class Format(models.TextChoices):
        SQUARE = "square", "Post cuadrado"
        STORY = "story", "Historia"
        PORTRAIT = "portrait", "Post vertical"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        READY = "ready", "Listo para generar"
        IN_REVIEW = "in_review", "En revisión"
        COMPLETED = "completed", "Completado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    format = models.CharField(max_length=16, choices=Format.choices)
    title = models.CharField(max_length=180)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT)
    campaign = models.ForeignKey(Campaign, null=True, blank=True, on_delete=models.PROTECT)
    audience = models.TextField()
    objective = models.TextField()
    requested_message = models.TextField(blank=True)
    source_references = models.JSONField(default=list)
    constraints = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
