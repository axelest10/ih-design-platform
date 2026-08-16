import pytest

from ai.models import AICallAudit
from ai.providers import GenerationRequest, GenerationResponse
from ai.services.audit import audited_generate
from ai.services.quality import validate_ai_output
from briefs.models import DesignBrief
from designs.models import Design, DesignVersion


@pytest.mark.django_db
def test_audited_generation_persists_prompt_response_model_and_design_version():
    brief = DesignBrief.objects.create(
        title="Auditoría IA",
        format=DesignBrief.Format.SQUARE,
        audience="Personas adultas",
        objective="Registrar una llamada",
    )
    design = Design.objects.create(brief=brief)
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"headline": "Prueba"},
    )

    class Provider:
        name = "test-provider"
        model = "test-model"

        def generate(self, request):
            return GenerationResponse("test-provider", "test-model", "Copy autorizado", {"id": "1"})

    response = audited_generate(
        Provider(),
        GenerationRequest("Escribe copy", {"source_status": "confirmed"}),
        design_version=version,
    )

    audit = AICallAudit.objects.get()
    assert response.content == "Copy autorizado"
    assert audit.provider == "test-provider"
    assert audit.model == "test-model"
    assert "Escribe copy" in audit.prompt
    assert audit.response == "Copy autorizado"
    assert audit.design_version_id == version.pk
    assert audit.quality_report["status"] == "passed"


def test_quality_validator_flags_unverified_numbers_urls_and_claims():
    report = validate_ai_output(
        "Oferta garantizado 99%: https://invented.example",
        {"benefit": "Evaluación", "source_url": "https://approved.example"},
    )

    assert report["status"] == "needs_review"
    assert {flag["type"] for flag in report["flags"]} == {
        "unverified_number",
        "unverified_url",
        "unverified_claim",
    }
