import json
from pathlib import Path

from django.conf import settings


def _catalog_products() -> list[dict]:
    path = Path(settings.BASE_DIR) / "brand" / "knowledge" / "product-catalog.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        product
        for product in payload.get("products", [])
        if product.get("status") != "deprecated"
    ]


def school_kit_products(country: str = "", priority: list[str] | None = None) -> list[dict]:
    # Axel confirmed these school-kit priorities on 2026-08-08.
    priority = priority or ["qc-2026", "teacher-training-certifications"]
    products = []
    for product in _catalog_products():
        countries = product.get("countries") or []
        if country and countries and country not in countries:
            continue
        products.append(
            {
                "product_slug": product["product_slug"],
                "canonical_name": product.get("canonical_name", product["product_slug"]),
                "brand_scope": product.get("brand_scope", "core"),
                "pillar": product.get("pillar"),
                "status": product.get("status", "needs_confirmation"),
                "needs_confirmation": product.get("needs_confirmation", False),
                "priority": product["product_slug"] in priority,
            }
        )
    priority_order = {slug: index for index, slug in enumerate(priority)}
    return sorted(
        products,
        key=lambda product: (
            0 if product["priority"] else 1,
            priority_order.get(product["product_slug"], len(priority)),
            product["canonical_name"],
        ),
    )


def sales_kit_products() -> list[dict]:
    """Devuelve todos los productos activos, sin inventar prioridades comerciales."""
    return [
        {
            "product_slug": product["product_slug"],
            "canonical_name": product.get("canonical_name", product["product_slug"]),
            "brand_scope": product.get("brand_scope", "core"),
            "pillar": product.get("pillar"),
            "status": product.get("status", "needs_confirmation"),
            "needs_confirmation": product.get("needs_confirmation", False),
            "priority": False,
        }
        for product in _catalog_products()
    ]

VENUE_KIT_DEFAULT_PRODUCT_SLUGS = [
    "general-english",
    "cambridge-exam-preparation",
    "university-programmes",
    "business-english",
    "ielts-preparation",
    "spanish-courses",
]


def venue_kit_products(priority: list[str] | None = None) -> list[dict]:
    """Return the shared six-pillar venue offer plus future catalogued options.

    Venue availability is explicitly confirmed by the client for the six defaults, so this
    helper intentionally does not apply the country inference filter used by school-kit.
    Additional active catalog products remain selectable without changing this default set.
    """
    priority = priority or VENUE_KIT_DEFAULT_PRODUCT_SLUGS
    products = []
    for product in _catalog_products():
        products.append(
            {
                "product_slug": product["product_slug"],
                "canonical_name": product.get("canonical_name", product["product_slug"]),
                "brand_scope": product.get("brand_scope", "core"),
                "pillar": product.get("pillar"),
                "status": product.get("status", "needs_confirmation"),
                "needs_confirmation": product.get("needs_confirmation", False),
                "availability_status": (
                    "confirmed_by_client"
                    if product["product_slug"] in VENUE_KIT_DEFAULT_PRODUCT_SLUGS
                    else "needs_confirmation"
                ),
                "priority": product["product_slug"] in priority,
            }
        )
    priority_order = {slug: index for index, slug in enumerate(priority)}
    return sorted(
        products,
        key=lambda product: (
            0 if product["priority"] else 1,
            priority_order.get(product["product_slug"], len(priority)),
            product["canonical_name"],
        ),
    )
