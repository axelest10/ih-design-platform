import uuid

from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models


class OfficialAsset(models.Model):
    class AssetType(models.TextChoices):
        LOGO = "logo", "Logo"
        ICON = "icon", "Ícono"
        IMAGE = "image", "Imagen"
        FONT = "font", "Tipografía"

    key = models.CharField(max_length=160, unique=True)
    asset_type = models.CharField(max_length=24, choices=AssetType.choices)
    file = models.FileField(upload_to="official-assets/")
    checksum = models.CharField(max_length=128, blank=True)
    usage_rules = models.JSONField(default=dict)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class UploadedLogo(models.Model):
    """Logo aportado desde un brief; disponible para reutilización explícita."""

    class LogoType(models.TextChoices):
        PARTNER = "partner", "Partner"
        BRANCH = "branch", "Sede"
        PRODUCT = "product", "Producto"
        SCHOOL = "school", "Escuela asociada"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        PENDING_CATALOG = "pending_catalog", "Pendiente de catálogo"
        AVAILABLE = "available", "Disponible para briefs"
        PROMOTED_OFFICIAL = "promoted_official", "Promovido a oficial"
        ARCHIVED = "archived", "Archivado"

    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file = models.FileField(
        upload_to="uploaded-logos/",
        validators=[FileExtensionValidator(["svg", "png", "jpg", "jpeg", "ai", "eps", "pdf"])],
    )
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=8, blank=True)
    logo_type = models.CharField(max_length=24, choices=LogoType.choices, default=LogoType.OTHER)
    variant = models.CharField(max_length=24, default="color")
    usage_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING_CATALOG
    )
    created_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_logos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ArtworkReference(models.Model):
    """Pieza aprobada o referencia visual separada de los activos oficiales de marca."""

    class ReferenceType(models.TextChoices):
        APPROVED_BASE = "approved_base", "Base aprobada"
        INSPIRATION = "inspiration", "Inspiración"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobada"
        REJECTED = "rejected", "Rechazada"
        ARCHIVED = "archived", "Archivada"

    key = models.CharField(max_length=160, unique=True)
    title = models.CharField(max_length=220)
    reference_type = models.CharField(
        max_length=24,
        choices=ReferenceType.choices,
        default=ReferenceType.INSPIRATION,
    )
    approval_status = models.CharField(
        max_length=16,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    file = models.FileField(upload_to="artwork-references/", blank=True)
    source_url = models.URLField(blank=True)
    source_folder_url = models.URLField(blank=True)
    source_file_name = models.CharField(max_length=220, blank=True)
    repository_path = models.CharField(max_length=320, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    brand_scope = models.CharField(max_length=120, default="international-house")
    country = models.CharField(max_length=4, blank=True)
    product_slug = models.CharField(max_length=80, blank=True)
    format = models.CharField(max_length=24, blank=True)
    tags = models.JSONField(default=list)
    usage_notes = models.TextField(blank=True)
    provenance = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="artwork_references",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
