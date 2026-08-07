import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from security.permissions import is_allowed_corporate_email


def test_corporate_email_requires_exact_domain():
    assert is_allowed_corporate_email("Persona@ihmexico.com")
    assert is_allowed_corporate_email("persona@ihsantiago.cl")
    assert not is_allowed_corporate_email("persona@sub.ihmexico.com")
    assert not is_allowed_corporate_email("persona@fake-ihmexico.com")
    assert not is_allowed_corporate_email("persona@gmail.com")


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_unauthenticated_user_cannot_access_brand_tokens():
    response = APIClient().get("/api/v1/branding/tokens/")

    assert response.status_code == 403


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_authorized_corporate_user_can_access_brand_tokens():
    user = get_user_model().objects.create_user(
        username="axel",
        email="axel@ihmexico.com",
        password="unused-for-session-test",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/branding/tokens/")

    assert response.status_code == 200


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_non_corporate_user_is_rejected():
    user = get_user_model().objects.create_user(
        username="external",
        email="external@gmail.com",
        password="unused-for-session-test",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/branding/tokens/")

    assert response.status_code == 403


@pytest.mark.corporate_auth
def test_health_endpoint_remains_public():
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_sync_corporate_roles_creates_expected_groups(capsys):
    call_command("sync_corporate_roles")

    assert set(Group.objects.values_list("name", flat=True)) == {
        "platform_admin",
        "marketing",
        "designer",
        "reviewer",
        "viewer",
    }


@pytest.mark.corporate_auth
@pytest.mark.django_db
def test_only_reviewer_or_admin_can_review_design():
    brief = DesignBrief.objects.create(
        title="Brief de seguridad",
        format=DesignBrief.Format.SQUARE,
        audience="Audiencia corporativa",
        objective="Validar permisos",
    )
    design = Design.objects.create(brief=brief)
    version = DesignVersion.objects.create(
        design=design,
        number=1,
        template_key="square-v1",
        render_data={"headline": "Título", "body": "Cuerpo"},
        asset_refs=[],
        validation_summary={"status": "passed"},
    )
    designer = get_user_model().objects.create_user(
        username="designer",
        email="designer@ihbogota.com",
    )
    designer.groups.add(Group.objects.create(name="designer"))
    client = APIClient()
    client.force_authenticate(user=designer)

    rejected = client.post(
        f"/api/v1/designs/{design.pk}/review/",
        {"decision": "approve", "version": version.number},
        format="json",
    )

    assert rejected.status_code == 403

    reviewer = get_user_model().objects.create_user(
        username="reviewer",
        email="reviewer@ihsantiago.cl",
    )
    reviewer.groups.add(Group.objects.create(name="reviewer"))
    client.force_authenticate(user=reviewer)
    approved = client.post(
        f"/api/v1/designs/{design.pk}/review/",
        {"decision": "approve", "version": version.number},
        format="json",
    )

    assert approved.status_code == 200
