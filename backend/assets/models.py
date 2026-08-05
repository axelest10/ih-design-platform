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
