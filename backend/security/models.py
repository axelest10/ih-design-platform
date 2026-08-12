from django.db import models


class PasswordResetToken(models.Model):
    """Registro de uso único; nunca persiste el token firmado en texto claro."""

    token_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
