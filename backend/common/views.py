from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from branding.services import loader
from briefs.models import DesignBrief
from designs.models import Design
from materials.models import MaterialType


@require_GET
def health(request):
    """Liveness probe independiente de autenticación, base de datos y DRF."""
    return JsonResponse({"status": "ok", "service": "ih-design-platform"})


@api_view(["GET"])
@permission_classes([AllowAny])
def stats_summary(request):
    """Agregados públicos para la home, sin contenido de briefs ni diseños."""
    manifest = loader.load_logo_manifest()
    approved_logos = [
        entry for entry in manifest.get("logos", []) if entry.get("approved") is True
    ]
    country_codes = sorted(
        {
            str(entry["country"]).strip().upper()
            for entry in approved_logos
            if entry.get("country")
        }
    )
    pending_review_statuses = (
        Design.Status.IN_REVIEW,
        Design.Status.SELF_REVIEW,
        Design.Status.TEST_READY,
        Design.Status.REVISION_REQUESTED,
    )
    return Response(
        {
            "logos": {"approved": len(approved_logos)},
            "material_types": {"active": MaterialType.objects.filter(active=True).count()},
            "countries": {
                "count": len(country_codes),
                "codes": country_codes,
                "source": "approved_logo_manifest",
            },
            "catalog": {
                "status": manifest.get("status"),
                "version": manifest.get("version"),
            },
            "workflow": {
                "briefs": DesignBrief.objects.count(),
                "designs": Design.objects.count(),
                "pending_review": Design.objects.filter(
                    status__in=pending_review_statuses
                ).count(),
                "approved": Design.objects.filter(status=Design.Status.APPROVED).count(),
            },
        }
    )
