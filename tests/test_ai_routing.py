from django.conf import settings

from ai.providers import AnthropicVisualReviewProvider, OpenAIProvider
from ai.services.routing import (
    DEFAULT_AI_PROVIDER_REGISTRY,
    TASK_POLICIES,
    AIFlowClassification,
    AIProviderCapability,
    AIProviderProductionStatus,
    AITaskType,
    select_provider,
)


def test_registry_keeps_certified_routes_and_marks_gemini_as_evaluation_only():
    assert DEFAULT_AI_PROVIDER_REGISTRY.keys == (
        "openai_generation",
        "anthropic_visual_review",
        "gemini_generation",
    )
    assert DEFAULT_AI_PROVIDER_REGISTRY.get("openai_generation").capability == (
        AIProviderCapability.GENERATE
    )
    assert DEFAULT_AI_PROVIDER_REGISTRY.get("anthropic_visual_review").capability == (
        AIProviderCapability.VISUAL_REVIEW
    )
    gemini = DEFAULT_AI_PROVIDER_REGISTRY.get("gemini_generation")
    assert gemini.capability == AIProviderCapability.GENERATE
    assert gemini.production_status == AIProviderProductionStatus.EVALUATION_ONLY


def test_phase_a_policies_classify_both_tasks_as_existing_certified_flows():
    assert set(TASK_POLICIES) == {
        AITaskType.COPY_DRAFT,
        AITaskType.AUTOMATIC_VISUAL_REVIEW,
    }
    assert all(
        policy.flow_classification == AIFlowClassification.EXISTING_CERTIFIED_FLOW
        for policy in TASK_POLICIES.values()
    )
    assert "gemini_generation" not in {
        policy.provider_key for policy in TASK_POLICIES.values()
    }


def test_gemini_registration_does_not_change_certified_provider_selection(settings):
    settings.OPENAI_API_KEY = "synthetic-openai-key"
    settings.OPENAI_MODEL = "certified-openai-model"
    settings.ANTHROPIC_API_KEY = "synthetic-anthropic-key"
    settings.ANTHROPIC_MODEL = "certified-anthropic-model"

    copy_selection = select_provider(AITaskType.COPY_DRAFT)
    review_selection = select_provider(AITaskType.AUTOMATIC_VISUAL_REVIEW)

    assert copy_selection.registration.key == "openai_generation"
    assert isinstance(copy_selection.provider, OpenAIProvider)
    assert copy_selection.provider.model == "certified-openai-model"
    assert review_selection.registration.key == "anthropic_visual_review"
    assert isinstance(review_selection.provider, AnthropicVisualReviewProvider)
    assert review_selection.provider.model == "certified-anthropic-model"


def test_ai_router_is_disabled_by_default():
    assert settings.AI_ROUTER_ENABLED is False


def test_gemini_credentials_and_model_are_empty_by_default():
    assert settings.GEMINI_API_KEY == ""
    assert settings.GEMINI_MODEL == ""
