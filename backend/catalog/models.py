from django.db import models


class Product(models.Model):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    official_copy = models.TextField(blank=True)
    commercial_data = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} — {self.name}"


class Branch(models.Model):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=180)
    city = models.CharField(max_length=120, blank=True)
    official_contact_data = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} — {self.name}"
