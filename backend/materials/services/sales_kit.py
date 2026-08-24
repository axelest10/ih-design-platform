"""Generación controlada de paquetes comerciales desde una Campaign autorizada."""
from __future__ import annotations

from datetime import date
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from ai.services import VisualReviewProvider, run_automatic_design_review
from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from designs.services.renderer import RenderValidationError, render_preview
from designs.services.renderer_document import render_document_preview
from designs.services.renderer_presentation import render_presentation_preview

from ..models import MaterialBundleItem, MaterialTemplate
from .catalog import sales_kit_products
from .school_kit import _next_test_number, _validate_logos

SALES_KIT_DELIVERABLES: tuple[dict[str, str], ...] = (
    {
        "key": "sales-square",
        "label": "Pieza comercial cuadrada",
        "format": "square",
        "template_key": "square-v1",
        "scope": "per-product",
    },
    {
        "key": "sales-story",
        "label": "Story comercial",
        "format": "story",
        "template_key": "story-v1",
        "scope": "per-product",
    },
    {
        "key": "sales-portrait",
        "label": "Pieza comercial vertical",
        "format": "portrait",
        "template_key": "portrait-v1",
        "scope": "per-product",
    },
    {
        "key": "sales-brochure",
        "label": "Brochure comercial A4",
        "format": "html",
        "template_key": "brochure-a4-v1",
        "scope": "per-bundle",
    },
    {
        "key": "sales-presentation",
        "label": "Presentación comercial",
        "format": "presentation",
        "template_key": "presentation-16x9-v1",
        "scope": "per-bundle",
    },
)


class SalesKitGenerationError(ValueError):
    """La campaña no está lista o el contenido no puede renderizarse."""


def sales_kit_deliverables() -> list[dict[str, str]]:
    return [dict(item) for item in SALES_KIT_DELIVERABLES]


def _campaign_snapshot(campaign) -> dict[str, Any]:
    offer_data = campaign.offer_data if isinstance(campaign.offer_data, dict) else {}
    return {
        "id": str(campaign.pk),
        "code": campaign.code,
        "name": campaign.name,
        "starts_on": campaign.starts_on.isoformat() if campaign.starts_on else None,
        "ends_on": campaign.ends_on.isoformat() if campaign.ends_on else None,
        "approved_copy": campaign.approved_copy,
        "offer_data": offer_data,
    }


def _validated_campaign(bundle):
    campaign = bundle.campaign
    if campaign is None:
        raise SalesKitGenerationError("El sales-kit necesita una campaña comercial autorizada.")
    today = date.today()
    if not campaign.is_active:
        raise SalesKitGenerationError("La campaña seleccionada no está activa.")
    if campaign.starts_on and campaign.starts_on > today:
        raise SalesKitGenerationError("La campaña todavía no está vigente.")
    if campaign.ends_on and campaign.ends_on < today:
        raise SalesKitGenerationError("La campaña seleccionada ya expiró.")
    if not campaign.approved_copy.strip():
        raise SalesKitGenerationError("La campaña no tiene copy aprobado.")
    offer_data = campaign.offer_data if isinstance(campaign.offer_data, dict) else {}
    required = ("source_status", "source_url", "benefit", "cta")
    missing = [key for key in required if not str(offer_data.get(key) or "").strip()]
    if missing:
        raise SalesKitGenerationError(
            "La campaña no tiene confirmados estos datos comerciales: "
            + ", ".join(missing)
            + "."
        )
    if offer_data["source_status"] != "confirmed":
        raise SalesKitGenerationError(
            "La campaña debe tener source_status='confirmed' antes de generar piezas."
        )
    return campaign, offer_data


def _catalog_product(product_slug: str) -> dict[str, Any]:
    product = next(
        (item for item in sales_kit_products() if item["product_slug"] == product_slug),
        None,
    )
    if product is None:
        raise SalesKitGenerationError(
            f"El producto '{product_slug}' no está disponible en el catálogo activo."
        )
    return product


def _copy_for_product(bundle, product: dict[str, Any], offer_data: dict[str, Any]):
    context = bundle.brief_context or {}
    scoped = (context.get("copy_by_product") or {}).get(product["product_slug"]) or {}
    headline = str(scoped.get("headline") or context.get("headline") or "").strip()
    if not headline:
        headline = str(bundle.campaign.name).strip()
    body = str(scoped.get("body") or context.get("body") or bundle.campaign.approved_copy).strip()
    benefit = str(offer_data["benefit"]).strip()
    if benefit not in body:
        body = f"{body}\n\nBeneficio: {benefit}"
    price = str(offer_data.get("price") or "").strip()
    currency = str(offer_data.get("currency") or "").strip()
    if price and price not in body:
        body = f"{body}\nPrecio: {price} {currency}".strip()
    validity_note = str(offer_data.get("validity_note") or "").strip()
    if validity_note and validity_note not in body:
        body = f"{body}\nVigencia: {validity_note}"
    return {
        "headline": headline,
        "body": body,
        "cta": str(offer_data["cta"]).strip(),
        "audience": str(
            scoped.get("audience")
            or context.get("audience")
            or offer_data.get("audience")
            or "Audiencia definida por Marketing"
        ).strip(),
        "objective": str(
            scoped.get("objective")
            or context.get("objective")
            or "Presentar la campaña comercial vigente"
        ).strip(),
    }


def _render_payload(deliverable, product_slug, copy, context, logo):
    return {
        "template_key": deliverable["template_key"],
        "product_slug": product_slug,
        "headline": copy["headline"],
        "body": copy["body"],
        "cta": copy["cta"],
        "eyebrow": str(context.get("eyebrow") or "International House").strip(),
        "logo_name": logo,
        "additional_logo_keys": context.get("additional_logo_keys") or [],
        "background_token": str(context.get("background_token") or "knowledge"),
        "accent_token": str(context.get("accent_token") or "knowledge"),
        "text_token": str(context.get("text_token") or "dark_navy"),
        "_allow_validation_warnings": True,
    }


@transaction.atomic
def generate_sales_kit(
    bundle,
    *,
    user=None,
    review_provider: VisualReviewProvider | None = None,
) -> list[Any]:
    if bundle.material_type.slug != "sales-kit":
        raise SalesKitGenerationError("Solo se puede generar este paquete desde un sales-kit.")
    if bundle.items.exists():
        raise SalesKitGenerationError(
            "Este paquete ya tiene piezas generadas; edítalo antes de generar uno nuevo."
        )
    campaign, offer_data = _validated_campaign(bundle)
    context = bundle.brief_context or {}
    brand_logo_key, additional_logo_keys = _validate_logos(context, bundle.country, user)
    products = [_catalog_product(slug) for slug in bundle.product_slugs]
    if campaign.product_id and campaign.product.code not in bundle.product_slugs:
        raise SalesKitGenerationError("La campaña y los productos seleccionados no coinciden.")
    snapshot = _campaign_snapshot(campaign)
    next_test_number = _next_test_number()
    items = []

    social_type = MaterialTemplate.objects.get(key="square-v1").material_type
    brochure_template = MaterialTemplate.objects.select_related("material_type").get(
        key="brochure-a4-v1", active=True
    )
    presentation_template = MaterialTemplate.objects.select_related("material_type").get(
        key="presentation-16x9-v1", active=True
    )

    for product in products:
        product_slug = product["product_slug"]
        copy = _copy_for_product(bundle, product, offer_data)
        for deliverable in SALES_KIT_DELIVERABLES[:3]:
            title = f"{bundle.name} · {product['canonical_name']} · {deliverable['label']}"
            brief = DesignBrief.objects.create(
                status=DesignBrief.Status.IN_REVIEW,
                format=deliverable["format"],
                title=title[:180],
                country=bundle.country,
                product_slug=product_slug,
                brand_logo_key=brand_logo_key,
                additional_logo_keys=additional_logo_keys,
                material_type=social_type,
                branch=bundle.branch,
                campaign=campaign,
                audience=copy["audience"],
                objective=copy["objective"],
                requested_message=copy["headline"],
                language=str(context.get("language") or "es"),
                channel=str(context.get("channel") or "sales"),
                brief_data={
                    **context,
                    "sales_kit": {
                        "bundle_id": str(bundle.pk),
                        "deliverable_key": deliverable["key"],
                        "template_key": deliverable["template_key"],
                        "campaign_snapshot": snapshot,
                        "product_slug": product_slug,
                    },
                },
                constraints={"source": "sales-kit", "template_key": deliverable["template_key"]},
                created_by=user if user and user.is_authenticated else None,
            )
            design = Design.objects.create(
                brief=brief,
                status=(
                    Design.Status.SELF_REVIEW
                    if settings.DESIGN_TEST_MODE
                    else Design.Status.IN_REVIEW
                ),
                test_number=next_test_number if settings.DESIGN_TEST_MODE else None,
            )
            if settings.DESIGN_TEST_MODE:
                next_test_number += 1
            try:
                rendered = render_preview(
                    _render_payload(deliverable, product_slug, copy, context, brand_logo_key)
                )
            except RenderValidationError as exc:
                raise SalesKitGenerationError(f"{title}: {exc}") from exc
            version = DesignVersion.objects.create(
                design=design,
                number=1,
                template_key=rendered.template_key,
                render_data={**rendered.data, "html": rendered.html, "svg": rendered.svg},
                asset_refs=rendered.asset_refs,
                validation_summary=rendered.validation_summary,
            )
            run_automatic_design_review(version, provider=review_provider)
            items.append(
                MaterialBundleItem.objects.create(
                    bundle=bundle,
                    brief=brief,
                    deliverable_key=f"{product_slug}-{deliverable['key']}",
                    sort_order=len(items),
                )
            )

    primary_product = products[0]
    copy = _copy_for_product(bundle, primary_product, offer_data)
    for deliverable, template in (
        (SALES_KIT_DELIVERABLES[3], brochure_template),
        (SALES_KIT_DELIVERABLES[4], presentation_template),
    ):
        title = f"{bundle.name} · {deliverable['label']}"
        brief = DesignBrief.objects.create(
            status=DesignBrief.Status.IN_REVIEW,
            format=deliverable["format"],
            title=title[:180],
            country=bundle.country,
            product_slug=primary_product["product_slug"],
            brand_logo_key=brand_logo_key,
            additional_logo_keys=additional_logo_keys,
            material_type=template.material_type,
            branch=bundle.branch,
            campaign=campaign,
            audience=copy["audience"],
            objective=copy["objective"],
            requested_message=copy["headline"],
            language=str(context.get("language") or "es"),
            channel="sales",
            brief_data={
                **context,
                "sales_kit": {
                    "bundle_id": str(bundle.pk),
                    "deliverable_key": deliverable["key"],
                    "template_key": template.key,
                    "scope": "per-bundle",
                    "campaign_snapshot": snapshot,
                    "product_slug": primary_product["product_slug"],
                },
                "content": {**copy, "campaign_offer": offer_data},
            },
            constraints={"source": "sales-kit", "template_key": template.key},
            created_by=user if user and user.is_authenticated else None,
        )
        design = Design.objects.create(
            brief=brief,
            status=(
                Design.Status.SELF_REVIEW
                if settings.DESIGN_TEST_MODE
                else Design.Status.IN_REVIEW
            ),
            test_number=next_test_number if settings.DESIGN_TEST_MODE else None,
        )
        if settings.DESIGN_TEST_MODE:
            next_test_number += 1
        payload = {"template_key": template.key, "logo_name": brand_logo_key, **copy}
        try:
            if deliverable["format"] == "html":
                rendered = render_document_preview(payload, material_type=template.material_type)
                path = default_storage.save(
                    f"generated-designs/{design.pk}/version-1.pdf", ContentFile(rendered.pdf)
                )
                render_data = {**rendered.data, "pdf_path": path}
                asset_refs = [*rendered.asset_refs, path]
            else:
                rendered = render_presentation_preview(
                    payload, material_type=template.material_type
                )
                path = default_storage.save(
                    f"generated-designs/{design.pk}/version-1.pptx", ContentFile(rendered.pptx)
                )
                render_data = {**rendered.data, "pptx_path": path}
                asset_refs = [*rendered.asset_refs, path]
        except RenderValidationError as exc:
            raise SalesKitGenerationError(f"{title}: {exc}") from exc
        version = DesignVersion.objects.create(
            design=design,
            number=1,
            template_key=template.key,
            render_data=render_data,
            asset_refs=asset_refs,
            validation_summary=rendered.validation_summary,
        )
        run_automatic_design_review(version, provider=review_provider)
        items.append(
            MaterialBundleItem.objects.create(
                bundle=bundle,
                brief=brief,
                deliverable_key=deliverable["key"],
                sort_order=len(items),
            )
        )

    bundle.status = bundle.Status.IN_REVIEW
    bundle.save(update_fields=["status", "updated_at"])
    return items
