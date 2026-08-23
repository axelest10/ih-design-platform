"""Sugerencias de copy IA acotadas a fuentes comerciales ya confirmadas."""
from __future__ import annotations

import json
import re
from typing import Any

from ai.providers import AIProviderError, GenerationRequest, OpenAIProvider
from ai.services.audit import audited_generate
from ai.services.routing import (
    AIRoutingError,
    AITaskType,
    ai_prompt_improvement_enabled,
    ai_router_enabled,
    routed_generate,
)

from .catalog import sales_kit_products, venue_kit_products
from .email_kit import EmailKitGenerationError, _campaign_snapshot, _validate_campaign
from .sales_kit import SalesKitGenerationError, _validated_campaign
from .sales_kit import _campaign_snapshot as sales_campaign_snapshot
from .venue_kit import _validate_branch


class AICopyDraftError(ValueError):
    """Los datos autorizados no permiten crear un borrador de copy."""


KIT_SLUGS = {"venue-kit", "sales-kit", "email-kit"}
COPY_DRAFT_INSTRUCTION = (
    "Devuelve solo JSON con headline, body y cta. Parafrasea únicamente los datos del "
    "authorized_context; no inventes precios, porcentajes, fechas, lugares, contactos, "
    "beneficios ni llamadas a la acción. Si no hay CTA confirmado, devuelve cta vacío."
)
COPY_SAFETY_REQUIREMENTS = (
    "No inventes precios, porcentajes, fechas, lugares, contactos, beneficios ni llamadas a la "
    "acción. Si no hay CTA confirmado, exige cta vacío."
)
MAX_IMPROVED_INSTRUCTION_LENGTH = 4000


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


def _improve_copy_instruction(
    original_instruction: str,
    authorized_context: dict[str, Any],
    *,
    bundle,
) -> tuple[str, dict[str, Any] | None]:
    if not ai_prompt_improvement_enabled():
        return original_instruction, None
    trace = {
        "attempted": True,
        "used": False,
        "instruction_source": "original",
    }
    improvement_request = GenerationRequest(
        instruction=(
            "Reescribe la INSTRUCCION_ORIGINAL para que sea más clara y precisa al solicitar un "
            "borrador de copy. Devuelve únicamente la instrucción mejorada en texto plano. "
            "Conserva explícitamente estas restricciones: no inventar precios, porcentajes, "
            "fechas, lugares, contactos, beneficios ni llamadas a la acción; si no hay CTA "
            "confirmado, debe pedirse un CTA vacío. No agregues datos que no existan en "
            "authorized_context.\n\n"
            f"INSTRUCCION_ORIGINAL:\n{original_instruction}"
        ),
        authorized_context=authorized_context,
        output_format="text",
    )
    try:
        response = routed_generate(
            AITaskType.PROMPT_IMPROVEMENT,
            improvement_request,
            material_bundle=bundle,
        )
    except (AIProviderError, AIRoutingError):
        return original_instruction, {**trace, "fallback_reason": "provider_error"}
    improved = response.content.strip() if isinstance(response.content, str) else ""
    if not improved or len(improved) > MAX_IMPROVED_INSTRUCTION_LENGTH:
        return original_instruction, {
            **trace,
            "provider": response.provider,
            "model": response.model,
            "fallback_reason": "invalid_response",
        }
    guarded_instruction = f"{improved}\n\nRestricciones obligatorias: {COPY_SAFETY_REQUIREMENTS}"
    return guarded_instruction, {
        "attempted": True,
        "used": True,
        "instruction_source": "improved",
        "provider": response.provider,
        "model": response.model,
    }


def suggest_copy_draft(bundle, *, provider=None) -> dict[str, Any]:
    """Genera y guarda un borrador pendiente de aprobación, sin aplicarlo a diseños."""
    if bundle.material_type.slug not in KIT_SLUGS:
        raise AICopyDraftError(
            "Las sugerencias IA solo están disponibles para venue, sales y email kit."
        )
    authorized_context = _authorized_context(bundle)
    instruction, prompt_improvement = _improve_copy_instruction(
        COPY_DRAFT_INSTRUCTION,
        authorized_context,
        bundle=bundle,
    )
    request = GenerationRequest(
        instruction=instruction,
        authorized_context=authorized_context,
        output_format="json",
    )
    try:
        if provider is None and ai_router_enabled():
            response = routed_generate(
                AITaskType.COPY_DRAFT,
                request,
                material_bundle=bundle,
            )
        else:
            response = audited_generate(
                provider or OpenAIProvider(),
                request,
                material_bundle=bundle,
            )
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
    if prompt_improvement is not None:
        draft["prompt_improvement"] = prompt_improvement
    context = dict(bundle.brief_context or {})
    context["ai_copy_draft"] = draft
    bundle.brief_context = context
    bundle.status = bundle.Status.DRAFT
    bundle.save(update_fields=["brief_context", "status", "updated_at"])
    return draft
