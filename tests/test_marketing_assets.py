from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from materials.models import MarketingAsset


def _role_client(role):
    user = get_user_model().objects.create_user(
        username=f"asset-{role}",
        email=f"asset-{role}@ihmexico.com",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_public_marketing_assets_only_expose_active_files_and_filters(tmp_path, monkeypatch):
    storage = FileSystemStorage(location=tmp_path, base_url="/media/")
    monkeypatch.setattr(MarketingAsset._meta.get_field("file"), "storage", storage)
    MarketingAsset.objects.create(
        brand="ih",
        country="MX",
        category="banner_linkedin",
        label="Banner México",
        file=SimpleUploadedFile("banner.png", b"png"),
    )
    MarketingAsset.objects.create(
        brand="ielts",
        country="",
        category="foto_perfil",
        label="IELTS oculto",
        file=SimpleUploadedFile("ielts.png", b"png"),
        active=False,
    )

    response = APIClient().get(
        "/api/v1/marketing-assets/",
        {"brand": "ih", "country": "MX", "category": "banner_linkedin"},
    )

    assert response.status_code == 200
    assert [item["label"] for item in response.json()] == ["Banner México"]
    assert response.json()[0]["file_url"].endswith("banner.png")
    assert response.json()[0]["category_label"] == "Banner de LinkedIn"


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_platform_admin_can_upload_and_deactivate_marketing_asset(tmp_path, monkeypatch):
    storage = FileSystemStorage(location=tmp_path, base_url="/media/")
    monkeypatch.setattr(MarketingAsset._meta.get_field("file"), "storage", storage)
    client, user = _role_client("platform_admin")

    created = client.post(
        "/api/v1/marketing-assets/",
        {
            "brand": "ih",
            "country": "co",
            "category": "template_ppt",
            "label": "Presentación Colombia",
            "file": SimpleUploadedFile(
                "presentacion.pptx",
                b"PK\x03\x04fake-pptx",
                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            "active": True,
        },
        format="multipart",
    )

    assert created.status_code == 201, created.json()
    asset = MarketingAsset.objects.get(pk=created.json()["id"])
    assert asset.country == "CO"
    assert asset.uploaded_by == user
    updated = client.patch(
        f"/api/v1/marketing-assets/{asset.pk}/",
        {"active": False},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["active"] is False
    assert APIClient().get("/api/v1/marketing-assets/").json() == []
    assert len(client.get("/api/v1/marketing-assets/").json()) == 1


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_non_admin_cannot_upload_marketing_asset():
    client, _ = _role_client("marketing")

    response = client.post(
        "/api/v1/marketing-assets/",
        {
            "brand": "ielts",
            "category": "foto_perfil",
            "label": "No permitido",
            "file": SimpleUploadedFile("profile.png", b"png"),
        },
        format="multipart",
    )

    assert response.status_code == 403
    assert not MarketingAsset.objects.exists()


@pytest.mark.django_db
def test_marketing_materials_page_is_public():
    response = APIClient().get("/marketing-materials.html")

    assert response.status_code == 200
    assert b"Materiales de Marketing" in response.content
    assert b"scripts/marketing-materials.js" in response.content


def test_admin_contains_real_marketing_asset_upload_form():
    html = Path("frontend/admin.html").read_text(encoding="utf-8")
    script = Path("frontend/scripts/admin.js").read_text(encoding="utf-8")
    home = Path("frontend/index.html").read_text(encoding="utf-8")
    panel = Path("frontend/panel.html").read_text(encoding="utf-8")

    assert 'id="marketing-asset-form"' in html
    assert 'type="file"' in html
    assert "/api/v1/marketing-assets/" in script
    assert "new FormData(event.currentTarget)" in script
    assert 'href="marketing-materials.html"' in home
    assert "Descargar materiales" in home
    assert 'href="marketing-materials.html"' in panel
