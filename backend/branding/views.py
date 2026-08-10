from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from security.permissions import (
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    RoleAwareViewSet,
)

from .models import BrandGuideline
from .serializers import BrandGuidelineSerializer
from .services import loader, validators


class BrandGuidelineViewSet(RoleAwareViewSet, ModelViewSet):
    queryset = BrandGuideline.objects.all()
    serializer_class = BrandGuidelineSerializer
    role_rules = {
        "create": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "partial_update": (ROLE_PLATFORM_ADMIN, ROLE_MARKETING),
        "destroy": (ROLE_PLATFORM_ADMIN,),
    }


# Catálogo público no sensible para el home: tokens, logos aprobados y validación de color.
# Briefs, uploads, /me y el resto del backend conservan el permiso corporativo global.
@api_view(["GET"])
@permission_classes([AllowAny])
def brand_tokens(request):
    """Expone la fuente única de tokens de marca (brand/*.yaml) como JSON de solo lectura.

    No reemplaza a /api/v1/branding/ (BrandGuideline en base de datos); este endpoint sirve
    directamente los archivos fuente de brand/ para consumo por herramientas externas
    (frontend, diseñadores, otros proyectos) sin pasar por la base de datos.
    """
    return Response(loader.load_all_tokens())


@api_view(["GET"])
@permission_classes([AllowAny])
def brand_logos(request):
    """Expone el catálogo de logos aprobado desde ``brand/assets/logos/manifest.yaml``.

    Filtros opcionales: ``scope``, ``country``, ``brand`` y ``variant``. La respuesta conserva
    el orden del manifest para que los consumidores puedan mostrar primero el artwork curado.
    """
    manifest = loader.load_logo_manifest()
    logos = []
    for entry in manifest.get("logos", []):
        if entry.get("approved") is not True:
            continue
        normalized = dict(entry)
        normalized.setdefault("scope", "core")
        normalized.setdefault("brand", "International House México")
        normalized.setdefault("country", "MX")
        logos.append(normalized)

    filters = {
        key: request.query_params.get(key)
        for key in ("scope", "country", "brand", "variant")
        if request.query_params.get(key)
    }
    for key, value in filters.items():
        logos = [entry for entry in logos if str(entry.get(key, "")) == value]

    return Response(
        {
            "version": manifest.get("version"),
            "status": manifest.get("status"),
            "count": len(logos),
            "filters": filters,
            "logos": logos,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def validate_color(request):
    """Valida un color HEX contra la paleta institucional y, opcionalmente, contra un pilar.

    Query params:
        hex: valor de color, p. ej. "#3B44B5" (requerido)
        pillar: slug de pilar/producto, p. ej. "cambridge" (opcional)
    """
    hex_value = request.query_params.get("hex", "")
    pillar = request.query_params.get("pillar")

    if pillar:
        result = validators.validate_product_color(pillar, hex_value)
    else:
        result = validators.validate_color_is_authorized(hex_value)

    return Response(
        {"hex": hex_value, "pillar": pillar, "is_valid": result.is_valid, "reason": result.reason},
        status=200,
    )
