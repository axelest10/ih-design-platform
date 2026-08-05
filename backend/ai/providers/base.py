from dataclasses import dataclass, field
from typing import Any, Protocol


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot fulfill a request."""


@dataclass(frozen=True)
class GenerationRequest:
    instruction: str
    authorized_context: dict[str, Any] = field(default_factory=dict)
    output_format: str = "text"


@dataclass(frozen=True)
class GenerationResponse:
    provider: str
    model: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class AIProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        ...
