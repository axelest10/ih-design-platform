import json
from pathlib import Path

from django.conf import settings

from assets.models import UploadedLogo
from branding.services import loader
from security.permissions import ROLE_PLATFORM_ADMIN

PRIMARY_PRODUCT_SLUGS = (
    "university-programmes",
    "business-english",
    "general-english",
    "ielts-preparation",
    "spanish-courses",
)

COUNTRY_LABELS = {
    "MX": "México",
    "CO": "Colombia",
    "CL": "Chile",
    "PE": "Perú",
}


def is_regional_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_staff
        or user.is_superuser
        or user.groups.filter(name=ROLE_PLATFORM_ADMIN).exists()
    )


def load_product_catalog() -> dict:
    path = Path(settings.BASE_DIR) / "brand" / "knowledge" / "product-catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def primary_products() -> list[dict]:
    catalog = load_product_catalog()
    colors = loader.load_product_colors().get("pillars", {})
    products = []
    for product in catalog.get("products", []):
        if product.get("product_slug") not in PRIMARY_PRODUCT_SLUGS:
            continue
        item = dict(product)
        pillar = product.get("pillar")
        item["authorized_color"] = colors.get(pillar, {})
        products.append(item)
    return products


def approved_logos_for_brief(country: str, user) -> list[dict]:
    regional_admin = is_regional_admin(user)
    entries = []
    for entry in loader.load_logo_manifest().get("logos", []):
        if entry.get("approved") is not True:
            continue
        if entry.get("format") not in {"svg", "png", "jpg", "jpeg"}:
            continue
        scope = entry.get("scope", "core")
        entry_country = entry.get("country")
        allowed = scope in {"partner", "sub-brand"}
        if scope == "regional":
            allowed = regional_admin or entry_country == country
        if scope == "global":
            allowed = regional_admin
        if allowed:
            entries.append(dict(entry))
    return entries


def brief_options(user, country: str | None = None) -> dict:
    selected_country = country or ""
    regional_admin = is_regional_admin(user)
    logos = approved_logos_for_brief(selected_country, user) if selected_country else []
    uploaded_logos = []
    if user and user.is_authenticated:
        uploaded_queryset = UploadedLogo.objects.exclude(status=UploadedLogo.Status.ARCHIVED)
        if not regional_admin:
            uploaded_queryset = uploaded_queryset.filter(created_by=user)
        uploaded_logos = [
            {
                "name": f"uploaded:{logo.key}",
                "brand": logo.name,
                "country": logo.country,
                "scope": "user-uploaded",
                "variant": logo.variant,
                "status": logo.status,
            }
            for logo in uploaded_queryset
        ]
    return {
        "countries": [
            {"code": code, "label": label} for code, label in COUNTRY_LABELS.items()
        ],
        "products": primary_products(),
        "logos": logos,
        "uploaded_logos": uploaded_logos,
        "regional_access": regional_admin,
        "regional_brand_notice": (
            "IH LATAM solo está disponible para perfiles con permiso regional y "
            "requiere un logo oficial cargado."
        ),
        "additional_logo_scopes": ["partner", "sub-brand", "regional"],
    }


def logo_entry(key: str) -> dict | None:
    return next(
        (
            entry
            for entry in loader.load_logo_manifest().get("logos", [])
            if entry.get("name") == key
        ),
        None,
    )


def validate_brief_logo_access(key: str, country: str, user) -> str | None:
    entry = logo_entry(key)
    if entry is None or entry.get("approved") is not True:
        return f"El logo '{key}' no existe en el catálogo oficial aprobado."
    if entry.get("scope") == "regional" and not is_regional_admin(user):
        if entry.get("country") != country:
            return "Solo puedes usar el logo IH de tu país o sede autorizada."
    if entry.get("scope") == "global" and not is_regional_admin(user):
        return "Este logo requiere permiso regional."
    return None


def validate_uploaded_logo_access(key: str, user) -> bool:
    try:
        uploaded = UploadedLogo.objects.get(key=key)
    except (UploadedLogo.DoesNotExist, ValueError):
        return False
    if uploaded.status == UploadedLogo.Status.ARCHIVED:
        return False
    return bool(
        user
        and user.is_authenticated
        and (is_regional_admin(user) or uploaded.created_by_id == user.pk)
    )
