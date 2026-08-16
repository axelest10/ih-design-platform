"""Persistencia común de llamadas IA para auditoría y calidad."""
from __future__ import annotations

import json
from typing import Any

from ai.models import AICallAudit

from .quality import validate_ai_output


def _prompt_text(instruction: str, context: dict[str, Any], output_format: str) -> str:
    return json.dumps(
        {
            "instruction": instruction,
            "authorized_context": context,
            "output_format": output_format,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def audited_generate(
    provider,
    request,
    *,
    brief=None,
    design_version=None,
    material_bundle=None,
):
    """Ejecuta una llamada y registra éxito/error sin cambiar el contrato del proveedor."""
    prompt = _prompt_text(request.instruction, request.authorized_context, request.output_format)
    provider_name = getattr(provider, "name", provider.__class__.__name__)
    model = getattr(provider, "model", "")
    try:
        response = provider.generate(request)
    except Exception as exc:
        AICallAudit.objects.create(
            provider=provider_name,
            model=model,
            prompt=prompt,
            response=str(exc),
            request_context=request.authorized_context,
            quality_report={"status": "error", "flags": [{"type": "provider_error"}]},
            status=AICallAudit.Status.ERROR,
            brief=brief,
            design_version=design_version,
            material_bundle=material_bundle,
        )
        raise
    AICallAudit.objects.create(
        provider=response.provider or provider_name,
        model=response.model or model,
        prompt=prompt,
        response=response.content,
        request_context=request.authorized_context,
        response_metadata=response.metadata,
        quality_report=validate_ai_output(response.content, request.authorized_context),
        status=AICallAudit.Status.COMPLETED,
        brief=brief,
        design_version=design_version,
        material_bundle=material_bundle,
    )
    return response


def record_visual_review(*, provider, request, result, error=None) -> AICallAudit:
    """Registra una revisión visual aunque el proveedor use un contrato distinto a generate()."""
    context = {
        "version_id": request.version_id,
        "design_id": request.design_id,
        "template_key": request.template_key,
        "validation_summary": request.validation_summary,
    }
    response_text = json.dumps(
        result.report if result else {"error": str(error)}, ensure_ascii=False
    )
    return AICallAudit.objects.create(
        provider=getattr(provider, "name", provider.__class__.__name__),
        model=getattr(provider, "model", ""),
        prompt=json.dumps(context, ensure_ascii=False, sort_keys=True),
        response=response_text,
        request_context=context,
        quality_report=validate_ai_output(response_text, context),
        status=AICallAudit.Status.ERROR if error else AICallAudit.Status.COMPLETED,
        design_version_id=request.version_id,
    )
