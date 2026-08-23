"""Adaptador Groq sobre la compatibilidad OpenAI ya disponible en el proyecto."""

from django.conf import settings

from .base import AIProviderError, GenerationRequest, GenerationResponse
from .openai_compatible import (
    ClientFactory,
    default_client_factory,
    generate_with_openai_compatible_client,
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client_factory: ClientFactory | None = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "GROQ_API_KEY", "")
        self.model = model if model is not None else getattr(
            settings, "GROQ_MODEL", DEFAULT_GROQ_MODEL
        )
        self.client_factory = client_factory or default_client_factory

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.api_key:
            raise AIProviderError("GROQ_API_KEY is not configured")
        return generate_with_openai_compatible_client(
            provider_name=self.name,
            provider_label="Groq",
            base_url=GROQ_BASE_URL,
            api_key=self.api_key,
            model=self.model,
            request=request,
            client_factory=self.client_factory,
        )
