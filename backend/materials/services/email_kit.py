"""Generación de emails exportables, sin envío ni integración con proveedores."""
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
from designs.services.renderer import RenderValidationError
from designs.services.renderer_email import render_email_preview

from ..models import MaterialBundleItem, MaterialTemplate
from .catalog import _catalog_products
from .school_kit import _next_test_number, _validate_logos

EMAIL_KIT_DELIVERABLES: tuple[dict[str, str], ...] = (
    {
        "key": "email-campaign",
        "label": "Email comercial",
        "format": "html",
        "template_key": "email-base-v1",
        "scope": "per-bundle",
    },
)


class EmailKitGenerationError(ValueError):
    """Datos incompletos o inseguros para generar un email exportable."""


def email_kit_deliverables() -> list[dict[str, str]]:
    return [dict(item) for item in EMAIL_KIT_DELIVERABLES]


def email_kit_products() -> list[dict[str, Any]]:
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


def _campaign_snapshot(campaign) -> dict[str, Any]:
    return {
        "id": str(campaign.pk),
        "code": campaign.code,
        "name": campaign.name,
        "starts_on": campaign.starts_on.isoformat() if campaign.starts_on else None,
        "ends_on": campaign.ends_on.isoformat() if campaign.ends_on else None,
        "approved_copy": campaign.approved_copy,
        "offer_data": campaign.offer_data if isinstance(campaign.offer_data, dict) else {},
    }


def _validate_campaign(campaign):
    if campaign is None:
        raise EmailKitGenerationError("El email necesita una campaña comercial autorizada.")
    today = date.today()
    if not campaign.is_active:
        raise EmailKitGenerationError("La campaña seleccionada no está activa.")
    if campaign.starts_on and campaign.starts_on > today:
        raise EmailKitGenerationError("La campaña todavía no está vigente.")
    if campaign.ends_on and campaign.ends_on < today:
        raise EmailKitGenerationError("La campaña seleccionada ya expiró.")
    if not campaign.approved_copy.strip():
        raise EmailKitGenerationError("La campaña no tiene copy aprobado.")
    offer_data = campaign.offer_data if isinstance(campaign.offer_data, dict) else {}
    required = ("source_status", "source_url", "benefit", "cta")
    missing = [key for key in required if not str(offer_data.get(key) or "").strip()]
    if missing or offer_data.get("source_status") != "confirmed":
        raise EmailKitGenerationError(
            "La campaña debe tener datos comerciales confirmados: "
            + ", ".join(missing or ["source_status=confirmed"])
            + "."
        )
    return offer_data


def _required_email_context(bundle, offer_data: dict[str, Any]) -> dict[str, str]:
    context = bundle.brief_context or {}
    values = {
        field: str(context.get(field) or "").strip()
        for field in (
            "subject",
            "preheader",
            "headline",
            "body",
            "cta_label",
            "cta_url",
            "unsubscribe_url",
        )
    }
    if not values["body"]:
        values["body"] = bundle.campaign.approved_copy.strip()
    if not values["cta_label"]:
        values["cta_label"] = str(offer_data.get("cta") or "").strip()
    if not values["headline"]:
        values["headline"] = bundle.campaign.name.strip()
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise EmailKitGenerationError(
            "Faltan campos obligatorios en brief_context: " + ", ".join(missing) + "."
        )
    return values


@transaction.atomic
def generate_email_kit(
    bundle,
    *,
    user=None,
    review_provider: VisualReviewProvider | None = None,
) -> list[Any]:
    if bundle.material_type.slug != "email-kit":
        raise EmailKitGenerationError("Solo se puede generar este paquete desde un email-kit.")
    if bundle.items.exists():
        raise EmailKitGenerationError(
            "Este paquete ya tiene piezas generadas; edítalo antes de generar uno nuevo."
        )
    offer_data = _validate_campaign(bundle.campaign)
    context = bundle.brief_context or {}
    values = _required_email_context(bundle, offer_data)
    brand_logo_key, additional_logo_keys = _validate_logos(context, bundle.country, user)
    template = MaterialTemplate.objects.select_related("material_type").get(
        key="email-base-v1", active=True
    )
    snapshot = _campaign_snapshot(bundle.campaign)
    next_test_number = _next_test_number()
    deliverable = EMAIL_KIT_DELIVERABLES[0]
    brief = DesignBrief.objects.create(
        status=DesignBrief.Status.IN_REVIEW,
        format=DesignBrief.Format.HTML,
        title=f"{bundle.name} · {deliverable['label']}"[:180],
        country=bundle.country,
        product_slug=(bundle.product_slugs or [""])[0],
        brand_logo_key=brand_logo_key,
        additional_logo_keys=additional_logo_keys,
        material_type=template.material_type,
        branch=bundle.branch,
        campaign=bundle.campaign,
        audience=str(context.get("audience") or "Audiencia definida por Marketing").strip(),
        objective=str(context.get("objective") or "Presentar la campaña por email").strip(),
        requested_message=values["headline"],
        language=str(context.get("language") or "es"),
        channel="email",
        brief_data={
            **context,
            "email_kit": {
                "bundle_id": str(bundle.pk),
                "deliverable_key": deliverable["key"],
                "template_key": template.key,
                "campaign_snapshot": snapshot,
                "sending": False,
                "export_only": True,
            },
            "content": values,
        },
        constraints={"source": "email-kit", "template_key": template.key},
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
    payload = {
        "template_key": template.key,
        "logo_name": brand_logo_key,
        "language": str(context.get("language") or "es"),
        **values,
    }
    try:
        rendered = render_email_preview(payload, material_type=template.material_type)
    except RenderValidationError as exc:
        raise EmailKitGenerationError(str(exc)) from exc
    html_path = default_storage.save(
        f"generated-designs/{design.pk}/version-1.html", ContentFile(rendered.html.encode())
    )
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key=rendered.template_key,
        render_data={**rendered.data, "html": rendered.html, "html_path": html_path},
        asset_refs=[*rendered.asset_refs, html_path],
        validation_summary=rendered.validation_summary,
    )
    run_automatic_design_review(version, provider=review_provider)
    item = MaterialBundleItem.objects.create(
        bundle=bundle,
        brief=brief,
        deliverable_key=deliverable["key"],
        sort_order=0,
    )
    bundle.status = bundle.Status.IN_REVIEW
    bundle.save(update_fields=["status", "updated_at"])
    return [item]
