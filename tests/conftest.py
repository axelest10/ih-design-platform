import pytest


@pytest.fixture(autouse=True)
def legacy_api_access(settings, request):
    """Mantiene los tests existentes locales; los tests de seguridad fuerzan el modo corporativo."""
    if request.node.get_closest_marker("corporate_auth"):
        settings.CORPORATE_AUTH_REQUIRED = True
    else:
        settings.CORPORATE_AUTH_REQUIRED = False
