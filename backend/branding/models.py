from django.db import models


class BrandGuideline(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    primary_color = models.CharField(max_length=7, default="#3B44B5")
    palette = models.JSONField(default=dict)
    typography = models.JSONField(default=dict)
    rules = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
