import pytest

from config.celery import app as celery_app


@pytest.fixture(autouse=True)
def legacy_api_access(settings, request):
    """Mantiene los tests existentes locales; los tests de seguridad fuerzan el modo corporativo."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    if request.node.get_closest_marker("corporate_auth"):
        settings.CORPORATE_AUTH_REQUIRED = True
    else:
        settings.CORPORATE_AUTH_REQUIRED = False
