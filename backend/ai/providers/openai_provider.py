from django.conf import settings

from .base import AIProviderError, GenerationRequest, GenerationResponse


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini")

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(
            model=self.model,
            instructions=(
                "You assist with authorized marketing briefs. Never invent prices, dates, "
                "locations, "
                "contacts, academic facts, logos, or critical text inside images."
            ),
            input={
                "instruction": request.instruction,
                "authorized_context": request.authorized_context,
                "output_format": request.output_format,
            },
        )
        return GenerationResponse(
            provider=self.name,
            model=self.model,
            content=response.output_text,
            metadata={"response_id": response.id},
        )
