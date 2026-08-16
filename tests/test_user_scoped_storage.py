from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from assets.models import UploadedLogo
from briefs.models import BriefReferenceUpload
from designs.services.storage_paths import generated_design_path
from materials.models import MarketingAsset


@pytest.mark.django_db
def test_uploaded_files_are_scoped_to_the_owner():
    user = get_user_model().objects.create_user(
        username="storage-owner",
        email="storage-owner@example.com",
    )
    assert UploadedLogo._meta.get_field("file").upload_to(
        UploadedLogo(created_by=user), "nested/logo.png"
    ) == f"users/{user.pk}/uploaded-logos/logo.png"
    assert BriefReferenceUpload._meta.get_field("file").upload_to(
        BriefReferenceUpload(created_by=user), "nested/reference.pdf"
    ) == f"users/{user.pk}/brief-references/reference.pdf"
    assert MarketingAsset._meta.get_field("file").upload_to(
        MarketingAsset(uploaded_by=user), "nested/banner.pptx"
    ) == f"users/{user.pk}/marketing-assets/banner.pptx"


def test_generated_design_files_are_scoped_to_the_brief_owner():
    design = SimpleNamespace(
        pk="design-123",
        brief=SimpleNamespace(created_by_id=42),
    )

    assert generated_design_path(design, "version-1.pdf") == (
        "users/42/generated-designs/design-123/version-1.pdf"
    )


def test_unowned_files_use_an_explicit_fallback_scope():
    assert UploadedLogo._meta.get_field("file").upload_to(
        UploadedLogo(), "logo.png"
    ) == "users/unassigned/uploaded-logos/logo.png"
