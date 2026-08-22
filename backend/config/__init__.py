"""Load the project Celery app whenever Django imports the config package."""

from .celery import app as celery_app

__all__ = ("celery_app",)
