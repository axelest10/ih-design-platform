from django.conf import settings

from ai.services.routing import (
    DEFAULT_AI_PROVIDER_REGISTRY,
    TASK_POLICIES,
    AIFlowClassification,
    AIProviderCapability,
    AITaskType,
)


def test_phase_a_registry_contains_only_current_certified_provider_routes():
    assert DEFAULT_AI_PROVIDER_REGISTRY.keys == (
        "openai_generation",
        "anthropic_visual_review",
    )
    assert DEFAULT_AI_PROVIDER_REGISTRY.get("openai_generation").capability == (
        AIProviderCapability.GENERATE
    )
    assert DEFAULT_AI_PROVIDER_REGISTRY.get("anthropic_visual_review").capability == (
        AIProviderCapability.VISUAL_REVIEW
    )


def test_phase_a_policies_classify_both_tasks_as_existing_certified_flows():
    assert set(TASK_POLICIES) == {
        AITaskType.COPY_DRAFT,
        AITaskType.AUTOMATIC_VISUAL_REVIEW,
    }
    assert all(
        policy.flow_classification == AIFlowClassification.EXISTING_CERTIFIED_FLOW
        for policy in TASK_POLICIES.values()
    )


def test_ai_router_is_disabled_by_default():
    assert settings.AI_ROUTER_ENABLED is False
