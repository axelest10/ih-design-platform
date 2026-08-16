"""Generación del bloque de copy editable para un brief."""
from ai.providers import AIProviderError, GenerationRequest, OpenAIProvider

from ..models import DesignBrief


def _authorized_context(brief: DesignBrief) -> dict:
    brief_data = brief.brief_data or {}
    return {
        "title": brief.title,
        "audience": brief.audience,
        "objective": brief.objective,
        "requested_message": brief.requested_message,
        "brief_data": {
            "audience_need": brief_data.get("audience_need", ""),
            "campaign_info": brief_data.get("campaign_info", ""),
            "required_information": brief_data.get("required_information", ""),
            "cta": brief_data.get("cta", ""),
            "cta_destination": brief_data.get("cta_destination", ""),
            "tone": brief_data.get("tone", ""),
            "visual_elements": brief_data.get("visual_elements", ""),
        },
        "language": brief.language,
        "channel": brief.channel,
    }


def generate_prompt_for_brief(brief: DesignBrief) -> None:
    """Genera copy publicitario editable, no un prompt para generar imágenes."""
    request = GenerationRequest(
        instruction=(
            "Escribe un solo bloque de copy publicitario en el idioma indicado por el brief, "
            "listo para que una persona lo revise y edite antes de adaptarlo a una pieza gráfica "
            "corta. El resultado debe ser texto natural corrido: no uses JSON, viñetas, listas ni "
            "markdown. Usa exclusivamente el contexto autorizado y no inventes precios, fechas, "
            "cupos, contactos, datos académicos ni logos."
        ),
        authorized_context=_authorized_context(brief),
        output_format="text",
    )

    try:
        response = OpenAIProvider().generate(request)
    except AIProviderError:
        brief.generated_prompt = ""
        brief.prompt_source = DesignBrief.PromptSource.MANUAL
        brief.save(update_fields=["generated_prompt", "prompt_source", "updated_at"])
        return

    brief.generated_prompt = response.content.strip()
    brief.prompt_source = DesignBrief.PromptSource.AI
    brief.status = DesignBrief.Status.READY
    brief.save(
        update_fields=["generated_prompt", "prompt_source", "status", "updated_at"]
    )
