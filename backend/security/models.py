from django.db import models


class MagicLinkToken(models.Model):
    """Registro de consumo; el token firmado nunca se persiste en texto claro."""

    token_hash = models.CharField(max_length=64, unique=True)
    email = models.EmailField(db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
