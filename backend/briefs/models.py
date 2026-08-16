import uuid

from django.contrib.auth import get_user_model
from django.db import models

from briefs.storage_paths import brief_reference_path
from campaigns.models import Campaign
from catalog.models import Branch, Product


class DesignBrief(models.Model):
    class Format(models.TextChoices):
        SQUARE = "square", "Post cuadrado"
        STORY = "story", "Historia"
        PORTRAIT = "portrait", "Post vertical"
        REEL = "reel", "Reel"
        CAROUSEL = "carousel", "Carrusel"
        BANNER = "banner", "Banner"
        PRESENTATION = "presentation", "Presentación"
        HTML = "html", "HTML"
        SVG = "svg", "SVG"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        READY = "ready", "Listo para generar"
        IN_REVIEW = "in_review", "En revisión"
        COMPLETED = "completed", "Completado"

    class PromptSource(models.TextChoices):
        AI = "ai", "IA"
        MANUAL = "manual", "Manual"
        AI_EDITED = "ai_edited", "IA editada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    format = models.CharField(max_length=16, choices=Format.choices)
    title = models.CharField(max_length=180)
    country = models.CharField(max_length=8, blank=True)
    product_slug = models.CharField(max_length=80, blank=True)
    brand_logo_key = models.CharField(max_length=160, blank=True)
    additional_logo_keys = models.JSONField(default=list)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    material_type = models.ForeignKey(
        "materials.MaterialType",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="briefs",
    )
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT)
    campaign = models.ForeignKey(Campaign, null=True, blank=True, on_delete=models.PROTECT)
    audience = models.TextField()
    objective = models.TextField()
    requested_message = models.TextField(blank=True)
    generated_prompt = models.TextField(blank=True, default="")
    prompt_source = models.CharField(
        max_length=16,
        choices=PromptSource.choices,
        blank=True,
        default="",
    )
    source_references = models.JSONField(default=list)
    visual_reference_urls = models.JSONField(default=list)
    language = models.CharField(max_length=12, default="es")
    channel = models.CharField(max_length=40, blank=True)
    brief_data = models.JSONField(default=dict)
    constraints = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="design_briefs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BriefReferenceUpload(models.Model):
    """Referencia visual aportada por quien crea el brief."""

    brief = models.ForeignKey(
        DesignBrief, on_delete=models.CASCADE, related_name="reference_uploads"
    )
    file = models.FileField(upload_to=brief_reference_path)
    caption = models.CharField(max_length=180, blank=True)
    created_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="brief_reference_uploads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
