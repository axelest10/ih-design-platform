from django.conf import settings

from config import celery_app


def test_django_boot_exposes_the_configured_celery_app():
    assert celery_app.main == "ih_design_platform"
    assert celery_app.conf.broker_url == settings.REDIS_URL
