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


class TransactionalEmailDelivery(models.Model):
    """Estado local de un correo sin persistir asunto, cuerpo, enlace ni token."""

    class Status(models.TextChoices):
        SUBMITTING = "submitting", "Submitting"
        ACCEPTED = "accepted", "Accepted"
        DELIVERED = "delivered", "Delivered"
        BOUNCED = "bounced", "Bounced"
        SPAM_COMPLAINT = "spam_complaint", "Spam complaint"
        SUPPRESSED = "suppressed", "Suppressed"
        REACTIVATED = "reactivated", "Reactivated"
        FAILED = "failed", "Failed"

    provider_message_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    recipient = models.EmailField(db_index=True)
    user = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactional_email_deliveries",
    )
    password_reset_token = models.OneToOneField(
        PasswordResetToken,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_delivery",
    )
    message_stream = models.CharField(max_length=64)
    tag = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SUBMITTING,
        db_index=True,
    )
    failure_category = models.CharField(max_length=64, blank=True)
    bounce_type = models.CharField(max_length=64, blank=True)
    bounce_type_code = models.PositiveIntegerField(null=True, blank=True)
    safe_reason = models.CharField(max_length=500, blank=True)
    suppressed = models.BooleanField(default=False)
    spam_complaint = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]


class EmailRecipientState(models.Model):
    """Supresión vigente de un destinatario conocido por la aplicación."""

    recipient = models.EmailField(unique=True)
    suppressed = models.BooleanField(default=False, db_index=True)
    suppression_reason = models.CharField(max_length=64, blank=True)
    spam_complaint = models.BooleanField(default=False)
    provider_changed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["recipient"]


class PostmarkWebhookEvent(models.Model):
    """Evento Postmark idempotente y deliberadamente libre de contenido del mensaje."""

    class EventType(models.TextChoices):
        DELIVERY = "Delivery", "Delivery"
        BOUNCE = "Bounce", "Bounce"
        SPAM_COMPLAINT = "SpamComplaint", "Spam complaint"
        SUBSCRIPTION_CHANGE = "SubscriptionChange", "Subscription change"

    event_key = models.CharField(max_length=64, unique=True)
    delivery = models.ForeignKey(
        TransactionalEmailDelivery,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="provider_events",
    )
    provider_message_id = models.CharField(max_length=64, blank=True, db_index=True)
    provider_event_id = models.CharField(max_length=64, blank=True)
    event_type = models.CharField(max_length=32, choices=EventType.choices, db_index=True)
    recipient = models.EmailField(db_index=True)
    occurred_at = models.DateTimeField(db_index=True)
    message_stream = models.CharField(max_length=64, blank=True)
    classification = models.CharField(max_length=64, blank=True)
    safe_detail = models.CharField(max_length=500, blank=True)
    suppress_sending = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
