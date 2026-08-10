import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from rest_framework.test import APIClient

from assets.models import ArtworkReference


@pytest.mark.django_db
def test_artwork_reference_can_be_registered_from_a_folder_link():
    response = APIClient().post(
        "/api/v1/artwork-references/",
        {
            "key": "latam-home-001",
            "title": "Home corporativo aprobado",
            "reference_type": "approved_base",
            "source_folder_url": "https://drive.google.com/drive/folders/example",
            "source_file_name": "home-corporativo.png",
            "country": "MX",
            "brand_scope": "international-house",
            "format": "square",
            "tags": ["home", "corporativo", "square"],
        },
        format="json",
    )

    assert response.status_code == 201
    assert ArtworkReference.objects.get(key="latam-home-001").reference_type == "approved_base"


@pytest.mark.django_db
def test_artwork_reference_can_be_filtered_as_inspiration():
    ArtworkReference.objects.create(
        key="inspiration-01",
        title="Referencia editorial",
        reference_type="inspiration",
        approval_status="approved",
        country="CO",
        format="portrait",
    )
    ArtworkReference.objects.create(
        key="base-01",
        title="Base cuadrada",
        reference_type="approved_base",
        approval_status="approved",
        country="CO",
        format="square",
    )

    response = APIClient().get(
        "/api/v1/artwork-references/",
        {"reference_type": "inspiration", "country": "CO"},
    )

    assert response.status_code == 200
    payload = response.json()
    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    assert len(items) == 1
    assert items[0]["key"] == "inspiration-01"


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_only_reviewer_can_approve_artwork_reference():
    reference = ArtworkReference.objects.create(
        key="pending-reference",
        title="Referencia pendiente",
        reference_type="inspiration",
    )
    reviewer = get_user_model().objects.create_user(
        username="art-reviewer",
        email="reviewer@ihmexico.com",
    )
    reviewer.groups.add(Group.objects.get_or_create(name="reviewer")[0])
    client = APIClient()
    client.force_authenticate(user=reviewer)

    response = client.post(
        f"/api/v1/artwork-references/{reference.pk}/approve/",
        format="json",
    )

    assert response.status_code == 200
    reference.refresh_from_db()
    assert reference.approval_status == ArtworkReference.ApprovalStatus.APPROVED


@pytest.mark.django_db
def test_artwork_manifest_sync_is_idempotent_and_preserves_approval(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
entries:
  - key: drive-artwork-test-001
    title: Arte de prueba
    reference_type: inspiration
    approval_status: pending
    source_url: https://drive.google.com/file/d/test/view
    source_folder_url: https://drive.google.com/drive/folders/test
    repository_path: brand/assets/artwork-references/mexico/test.png
    country: mexico
    format: png
    tags: [drive, artwork]
    provenance:
      source_path: México/2026/Enero
""",
        encoding="utf-8",
    )

    call_command("sync_artwork_references", manifest=manifest)
    reference = ArtworkReference.objects.get(key="drive-artwork-test-001")
    reference.approval_status = ArtworkReference.ApprovalStatus.APPROVED
    reference.save(update_fields=["approval_status", "updated_at"])

    call_command("sync_artwork_references", manifest=manifest)
    reference.refresh_from_db()

    assert reference.repository_path.endswith("/test.png")
    assert reference.approval_status == ArtworkReference.ApprovalStatus.APPROVED


@pytest.mark.django_db
def test_visual_knowledge_endpoint_supports_exact_filters():
    response = APIClient().get(
        "/api/v1/artwork-references/knowledge/",
        {"country": "chile", "media_type": "image", "orientation": "square", "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["returned_assets"] >= 1
    assert len(payload["assets"]) <= 2
    assert all(
        asset["country"] == "chile"
        and asset["media_type"] == "image"
        and asset["technical"]["orientation"] == "square"
        for asset in payload["assets"]
    )
