from django.db import models

from catalog.models import Product


class Campaign(models.Model):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=180)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    approved_copy = models.TextField(blank=True)
    offer_data = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} — {self.name}"
