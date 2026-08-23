"""Routing mínimo para los flujos de IA certificados existentes.

La Fase A registra únicamente los proveedores actuales y no puntúa ni sustituye candidatos.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from .audit import audited_generate


class AIRoutingError(RuntimeError):
    """La política o el proveedor requerido no está registrado."""


class AITaskType:
    COPY_DRAFT = "copy_draft"
    AUTOMATIC_VISUAL_REVIEW = "automatic_visual_review"


class AIFlowClassification:
    EXISTING_CERTIFIED_FLOW = "existing_certified_flow"


class AIProviderCapability:
    GENERATE = "generate"
    VISUAL_REVIEW = "visual_review"


class AIProviderProductionStatus:
    PRODUCTION = "production"
    EVALUATION_ONLY = "evaluation_only"


@dataclass(frozen=True)
class AITaskPolicy:
    task_type: str
    flow_classification: str
    provider_key: str
    route_id: str
    selection_reason: str


@dataclass(frozen=True)
class AIProviderRegistration:
    key: str
    capability: str
    factory: Callable[[], Any]
    production_status: str = AIProviderProductionStatus.PRODUCTION


@dataclass(frozen=True)
class AIRouteSelection:
    policy: AITaskPolicy
    registration: AIProviderRegistration
    provider: Any

    @property
    def audit_metadata(self) -> dict[str, str]:
        return {
            "route_id": self.policy.route_id,
            "task_type": self.policy.task_type,
            "flow_classification": self.policy.flow_classification,
            "selection_reason": self.policy.selection_reason,
        }


class AIProviderRegistry:
    """Registro explícito y pequeño de factories de proveedores autorizados."""

    def __init__(self, registrations: tuple[AIProviderRegistration, ...]):
        self._registrations = {registration.key: registration for registration in registrations}
        if len(self._registrations) != len(registrations):
            raise ValueError("Las claves del registro de proveedores IA deben ser únicas.")

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._registrations)

    def get(self, key: str) -> AIProviderRegistration:
        try:
            return self._registrations[key]
        except KeyError as exc:
            raise AIRoutingError(f"Proveedor IA no registrado: {key}.") from exc


def _openai_provider():
    from ai.providers.openai_provider import OpenAIProvider

    return OpenAIProvider()


def _configured_anthropic_visual_review_provider():
    # La importación tardía evita el ciclo con el Protocol visual y reutiliza la selección actual.
    from .design_review import configured_visual_review_provider

    return configured_visual_review_provider()


def _gemini_provider():
    from ai.providers.gemini_provider import GeminiProvider

    return GeminiProvider()


DEFAULT_AI_PROVIDER_REGISTRY = AIProviderRegistry(
    (
        AIProviderRegistration(
            key="openai_generation",
            capability=AIProviderCapability.GENERATE,
            factory=_openai_provider,
        ),
        AIProviderRegistration(
            key="anthropic_visual_review",
            capability=AIProviderCapability.VISUAL_REVIEW,
            factory=_configured_anthropic_visual_review_provider,
        ),
        AIProviderRegistration(
            key="gemini_generation",
            capability=AIProviderCapability.GENERATE,
            factory=_gemini_provider,
            production_status=AIProviderProductionStatus.EVALUATION_ONLY,
        ),
    )
)

TASK_POLICIES = {
    AITaskType.COPY_DRAFT: AITaskPolicy(
        task_type=AITaskType.COPY_DRAFT,
        flow_classification=AIFlowClassification.EXISTING_CERTIFIED_FLOW,
        provider_key="openai_generation",
        route_id="existing-copy-draft-openai-v1",
        selection_reason="existing_certified_flow, único candidato",
    ),
    AITaskType.AUTOMATIC_VISUAL_REVIEW: AITaskPolicy(
        task_type=AITaskType.AUTOMATIC_VISUAL_REVIEW,
        flow_classification=AIFlowClassification.EXISTING_CERTIFIED_FLOW,
        provider_key="anthropic_visual_review",
        route_id="existing-visual-review-anthropic-v1",
        selection_reason="existing_certified_flow, único candidato",
    ),
}


def ai_router_enabled() -> bool:
    return bool(getattr(settings, "AI_ROUTER_ENABLED", False))


def select_provider(
    task_type: str,
    *,
    registry: AIProviderRegistry = DEFAULT_AI_PROVIDER_REGISTRY,
) -> AIRouteSelection:
    try:
        policy = TASK_POLICIES[task_type]
    except KeyError as exc:
        raise AIRoutingError(f"Tarea IA sin política: {task_type}.") from exc
    registration = registry.get(policy.provider_key)
    return AIRouteSelection(
        policy=policy,
        registration=registration,
        provider=registration.factory(),
    )


def routed_generate(
    task_type: str,
    request,
    *,
    brief=None,
    design_version=None,
    material_bundle=None,
    registry: AIProviderRegistry = DEFAULT_AI_PROVIDER_REGISTRY,
):
    """Selecciona el candidato certificado y conserva la auditoría existente."""
    selection = select_provider(task_type, registry=registry)
    if selection.registration.capability != AIProviderCapability.GENERATE:
        raise AIRoutingError(f"La tarea {task_type} no usa el contrato generate().")
    return audited_generate(
        selection.provider,
        request,
        brief=brief,
        design_version=design_version,
        material_bundle=material_bundle,
        audit_metadata=selection.audit_metadata,
    )
