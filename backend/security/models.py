from django.core.exceptions import ValidationError
from django.db import models


class ImmutableHubIdentityQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if {"hub_subject", "initial_email"}.intersection(kwargs):
            raise ValidationError("El subject y correo inicial del Hub son inmutables.")
        return super().update(**kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        if {"hub_subject", "initial_email"}.intersection(fields):
            raise ValidationError("El subject y correo inicial del Hub son inmutables.")
        return super().bulk_update(objs, fields, batch_size=batch_size)

    def delete(self):
        raise ValidationError("Los enlaces de identidad no se eliminan.")


class AppendOnlyIdentityEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if set(kwargs).issubset({"user", "user_id"}) and all(
            value is None for value in kwargs.values()
        ):
            return super().update(**kwargs)
        raise ValidationError("Los eventos de identidad son append-only.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Los eventos de identidad son append-only.")

    def delete(self):
        raise ValidationError("Los eventos de identidad no se eliminan.")


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


class HubIdentity(models.Model):
    """Enlace inmutable entre el subject del Hub y un usuario local de Design."""

    class LinkSource(models.TextChoices):
        LINKED_EXISTING = "linked_existing", "Linked existing user"
        PROVISIONED = "provisioned", "Provisioned least-privilege user"

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="hub_identity",
    )
    hub_subject = models.CharField(max_length=255, unique=True, editable=False)
    initial_email = models.EmailField(max_length=254, unique=True, editable=False)
    email_snapshot = models.EmailField(max_length=254)
    link_source = models.CharField(max_length=32, choices=LinkSource.choices)
    linked_at = models.DateTimeField(auto_now_add=True)
    last_authenticated_at = models.DateTimeField()
    objects = ImmutableHubIdentityQuerySet.as_manager()

    class Meta:
        ordering = ["hub_subject"]
        indexes = [models.Index(fields=["last_authenticated_at"])]

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.only("hub_subject", "initial_email").get(pk=self.pk)
            if (
                previous.hub_subject != self.hub_subject
                or previous.initial_email != self.initial_email
            ):
                raise ValidationError("El subject y correo inicial del Hub son inmutables.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los enlaces de identidad no se eliminan.")


class HubIdentityEvent(models.Model):
    """Auditoría append-only del ciclo de autenticación OIDC."""

    class EventType(models.TextChoices):
        LINKED = "linked", "Existing user linked"
        PROVISIONED = "provisioned", "User provisioned"
        LOGIN_SUCCESS = "login_success", "Login succeeded"
        LOGIN_DENIED = "login_denied", "Login denied"

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"

    event_type = models.CharField(max_length=32, choices=EventType.choices)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    user = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hub_identity_events",
    )
    hub_subject = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    objects = AppendOnlyIdentityEventQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Los eventos de identidad son append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los eventos de identidad no se eliminan.")
