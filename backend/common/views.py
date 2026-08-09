from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """Liveness probe independiente de autenticación, base de datos y DRF."""
    return JsonResponse({"status": "ok", "service": "ih-design-platform"})
