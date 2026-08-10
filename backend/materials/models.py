import uuid

from django.contrib.auth import get_user_model
from django.db import models

from briefs.models import DesignBrief
from campaigns.models import Campaign
from catalog.models import Branch


class MaterialType(models.Model):
    class RendererFamily(models.TextChoices):
        HTML_SVG = "html-svg", "HTML/SVG"
        EMAIL_HTML = "email-html", "Email HTML"
        DOCUMENT = "document", "Documento"
        PRESENTATION = "presentation", "Presentación"

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=180)
    renderer_family = models.CharField(max_length=32, choices=RendererFamily.choices)
    channel = models.CharField(max_length=40)
    schema_version = models.CharField(max_length=24, default="1.0.0")
    supported_formats = models.JSONField(default=list)
    priority_product_slugs = models.JSONField(default=list)
    product_scope = models.CharField(max_length=24, default="all_catalog")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]


class MaterialTemplate(models.Model):
    material_type = models.ForeignKey(
        MaterialType, on_delete=models.PROTECT, related_name="templates"
    )
    key = models.CharField(max_length=120, unique=True)
    version = models.CharField(max_length=24, default="1.0.0")
    dimensions = models.JSONField(default=dict)
    output_formats = models.JSONField(default=list)
    required_fields = models.JSONField(default=list)
    constraints = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["key", "-version"]


class MaterialBundle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        READY = "ready", "Listo para producción"
        IN_REVIEW = "in_review", "En revisión"
        COMPLETED = "completed", "Completado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    material_type = models.ForeignKey(
        MaterialType, on_delete=models.PROTECT, related_name="bundles"
    )
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=8, blank=True)
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT)
    campaign = models.ForeignKey(Campaign, null=True, blank=True, on_delete=models.PROTECT)
    product_slugs = models.JSONField(default=list)
    brief_context = models.JSONField(default=dict)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="material_bundles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class MaterialBundleItem(models.Model):
    bundle = models.ForeignKey(MaterialBundle, on_delete=models.CASCADE, related_name="items")
    brief = models.OneToOneField(
        DesignBrief, on_delete=models.PROTECT, related_name="material_bundle_item"
    )
    deliverable_key = models.SlugField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "deliverable_key"]
