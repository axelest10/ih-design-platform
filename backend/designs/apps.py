from django.apps import AppConfig


class DesignsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "designs"

    def ready(self):
        from . import signals  # noqa: F401
