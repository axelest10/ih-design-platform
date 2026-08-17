"""Sugerencias de copy IA acotadas a fuentes comerciales ya confirmadas."""
from __future__ import annotations

import json
import re
from typing import Any

from ai.providers import AIProviderError, GenerationRequest, OpenAIProvider

from .catalog import sales_kit_products, venue_kit_products
from .email_kit import EmailKitGenerationError, _campaign_snapshot, _validate_campaign
from .sales_kit import SalesKitGenerationError, _validated_campaign
from .sales_kit import _campaign_snapshot as sales_campaign_snapshot
from .venue_kit import _validate_branch


class AICopyDraftError(ValueError):
    """Los datos autorizados no permiten crear un borrador de copy."""


KIT_SLUGS = {"venue-kit", "sales-kit", "email-kit"}


def _confirmed_products(bundle) -> list[dict[str, Any]]:
    products = (
        venue_kit_products()
        if bundle.material_type.slug == "venue-kit"
        else sales_kit_products()
    )
    selected = set(bundle.product_slugs or [])
    if not selected and bundle.campaign_id and bundle.campaign.product_id:
        selected = {bundle.campaign.product.code}
    selected_products = [product for product in products if product["product_slug"] in selected]
    missing = sorted(selected - {product["product_slug"] for product in selected_products})
    if missing:
        raise AICopyDraftError("No hay datos de catálogo para: " + ", ".join(missing) + ".")
    unconfirmed = [
        product["product_slug"]
        for product in selected_products
        if (
            product.get("needs_confirmation")
            and not (
                bundle.material_type.slug == "venue-kit"
                and product.get("availability_status") == "confirmed_by_client"
            )
        )
        or product.get("status") != "confirmed"
    ]
    if unconfirmed:
        raise AICopyDraftError(
            "El copy IA solo puede usar productos confirmados: " + ", ".join(unconfirmed) + "."
        )
    return selected_products


def _authorized_context(bundle) -> dict[str, Any]:
    products = _confirmed_products(bundle)
    context: dict[str, Any] = {
        "kit": bundle.material_type.slug,
        "source_status": "confirmed",
        "products": [
            {
                "product_slug": product["product_slug"],
                "canonical_name": product["canonical_name"],
                "pillar": product.get("pillar"),
                "availability_status": product.get("availability_status", "confirmed"),
            }
            for product in products
        ],
    }
    if bundle.material_type.slug == "venue-kit":
        context["branch"] = _validate_branch(bundle)
        cta = (bundle.brief_context or {}).get("cta")
        if cta and (bundle.brief_context or {}).get("cta_source_status") == "confirmed":
            context["cta"] = cta
    else:
        try:
            if bundle.material_type.slug == "email-kit":
                offer_data = _validate_campaign(bundle.campaign)
                context["campaign"] = _campaign_snapshot(bundle.campaign)
            else:
                campaign, offer_data = _validated_campaign(bundle)
                context["campaign"] = sales_campaign_snapshot(campaign)
        except (EmailKitGenerationError, SalesKitGenerationError) as exc:
            raise AICopyDraftError(str(exc)) from exc
        context["offer"] = {
            key: value
            for key, value in offer_data.items()
            if key in {"source_status", "source_url", "benefit", "audience", "cta", "validity_note"}
        }
        context["cta"] = str(offer_data.get("cta") or "").strip()
    return context


def _parse_copy(content: str, authorized_context: dict[str, Any]) -> dict[str, str]:
    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AICopyDraftError("El proveedor IA debe devolver un objeto JSON de copy.") from exc
    if not isinstance(payload, dict):
        raise AICopyDraftError("El proveedor IA debe devolver un objeto JSON de copy.")
    copy = {
        field: str(payload.get(field) or "").strip()
        for field in ("headline", "body", "cta")
    }
    if not copy["headline"] or not copy["body"]:
        raise AICopyDraftError("El borrador IA debe incluir headline y body.")
    authorized_text = json.dumps(authorized_context, ensure_ascii=False)
    generated_text = copy["headline"] + " " + copy["body"]
    unauthorized_numbers = set(
        re.findall(r"\b\d+(?:[.,]\d+)?\b", generated_text)
    ) - set(
        re.findall(r"\b\d+(?:[.,]\d+)?\b", authorized_text)
    )
    if unauthorized_numbers:
        raise AICopyDraftError(
            "El borrador contiene cifras que no están en las fuentes confirmadas."
        )
    if copy["cta"] and copy["cta"] != str(authorized_context.get("cta") or "").strip():
        raise AICopyDraftError("El CTA sugerido debe coincidir con el CTA confirmado.")
    return copy


def suggest_copy_draft(bundle, *, provider=None) -> dict[str, Any]:
    """Genera y guarda un borrador pendiente de aprobación, sin aplicarlo a diseños."""
    if bundle.material_type.slug not in KIT_SLUGS:
        raise AICopyDraftError(
            "Las sugerencias IA solo están disponibles para venue, sales y email kit."
        )
    authorized_context = _authorized_context(bundle)
    provider = provider or OpenAIProvider()
    request = GenerationRequest(
        instruction=(
            "Devuelve solo JSON con headline, body y cta. Parafrasea únicamente los datos del "
            "authorized_context; no inventes precios, porcentajes, fechas, lugares, contactos, "
            "beneficios ni llamadas a la acción. Si no hay CTA confirmado, devuelve cta vacío."
        ),
        authorized_context=authorized_context,
        output_format="json",
    )
    try:
        response = provider.generate(request)
    except AIProviderError as exc:
        raise AICopyDraftError(str(exc)) from exc
    copy = _parse_copy(response.content, authorized_context)
    draft = {
        "status": "pending_approval",
        "source_status": "ai_draft",
        "needs_confirmation": True,
        "provider": response.provider,
        "model": response.model,
        "copy": copy,
        "authorized_context": authorized_context,
    }
    context = dict(bundle.brief_context or {})
    context["ai_copy_draft"] = draft
    bundle.brief_context = context
    bundle.status = bundle.Status.DRAFT
    bundle.save(update_fields=["brief_context", "status", "updated_at"])
    return draft
