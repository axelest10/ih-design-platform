import pytest
from rest_framework.test import APIClient

from branding.services import loader
from briefs.models import DesignBrief
from designs.models import Design
from materials.models import MaterialType


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_public_stats_summary_returns_only_real_aggregates():
    brief = DesignBrief.objects.create(
        format=DesignBrief.Format.SQUARE,
        title="Dato que nunca debe exponerse",
        audience="Audiencia privada",
        objective="Objetivo privado",
    )
    Design.objects.create(brief=brief, status=Design.Status.SELF_REVIEW)

    response = APIClient().get("/api/v1/stats/summary/")

    assert response.status_code == 200
    payload = response.json()
    manifest = loader.load_logo_manifest()
    approved = [entry for entry in manifest["logos"] if entry.get("approved") is True]
    assert payload["logos"]["approved"] == len(approved)
    assert payload["material_types"]["active"] == MaterialType.objects.filter(
        active=True
    ).count()
    assert payload["countries"] == {
        "count": 4,
        "codes": ["CL", "CO", "MX", "PE"],
        "source": "approved_logo_manifest",
    }
    assert payload["catalog"] == {
        "status": manifest["status"],
        "version": manifest["version"],
    }
    assert payload["workflow"] == {
        "briefs": 1,
        "designs": 1,
        "pending_review": 1,
        "approved": 0,
    }
    assert "Dato que nunca debe exponerse" not in response.content.decode()
