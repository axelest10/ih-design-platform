from django.db.models.signals import post_save
from django.dispatch import receiver

from common.observability import operation_event

from .models import DesignVersion
from .services.safe_zone import check_design_version


@receiver(post_save, sender=DesignVersion)
def log_design_version_created(sender, instance, created, **kwargs):
    if not created:
        return
    summary = dict(instance.validation_summary or {})
    safe_zone_check = check_design_version(instance)
    summary["safe_zone_check"] = safe_zone_check
    if safe_zone_check["status"] == "needs_changes":
        summary["status"] = "needs_changes"
    instance.validation_summary = summary
    instance.save(update_fields=["validation_summary"])
    operation_event(
        "design.version_created",
        design_id=instance.design_id,
        version_id=instance.pk,
        version_number=instance.number,
        template_key=instance.template_key,
    )
