"""Adaptador OpenRouter con un modelo explícito y sin router aleatorio."""

from django.conf import settings

from .base import AIProviderError, GenerationRequest, GenerationResponse
from .openai_compatible import (
    ClientFactory,
    default_client_factory,
    generate_with_openai_compatible_client,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client_factory: ClientFactory | None = None,
    ):
        self.api_key = (
            api_key if api_key is not None else getattr(settings, "OPENROUTER_API_KEY", "")
        )
        self.model = model if model is not None else getattr(settings, "OPENROUTER_MODEL", "")
        self.client_factory = client_factory or default_client_factory

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.api_key or not self.model:
            raise AIProviderError(
                "OpenRouter requiere OPENROUTER_API_KEY y OPENROUTER_MODEL configurados "
                "explícitamente."
            )
        if self.model == "openrouter/free":
            raise AIProviderError(
                "OPENROUTER_MODEL debe ser un modelo fijo; openrouter/free no está permitido."
            )
        return generate_with_openai_compatible_client(
            provider_name=self.name,
            provider_label="OpenRouter",
            base_url=OPENROUTER_BASE_URL,
            api_key=self.api_key,
            model=self.model,
            request=request,
            client_factory=self.client_factory,
        )
