from django.db.models.signals import post_save
from django.dispatch import receiver

from common.observability import operation_event

from .models import DesignVersion


@receiver(post_save, sender=DesignVersion)
def log_design_version_created(sender, instance, created, **kwargs):
    if not created:
        return
    operation_event(
        "design.version_created",
        design_id=instance.design_id,
        version_id=instance.pk,
        version_number=instance.number,
        template_key=instance.template_key,
    )
