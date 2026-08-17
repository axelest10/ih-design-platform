from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from assets.views import UploadedLogoViewSet
from briefs.views import DesignBriefViewSet
from designs.views import DesignViewSet
from materials.views import (
    MarketingAssetViewSet,
    MaterialBundleViewSet,
    MaterialTemplateViewSet,
    MaterialTypeViewSet,
)
from security.permissions import (
    CORPORATE_ROLES,
    ROLE_DESIGNER,
    ROLE_MARKETING,
    ROLE_PLATFORM_ADMIN,
    ROLE_REVIEWER,
    ROLE_VIEWER,
    RolePermission,
)

pytestmark = pytest.mark.corporate_auth

DESIGN_CREATORS = {ROLE_PLATFORM_ADMIN, ROLE_MARKETING, ROLE_DESIGNER}
HUMAN_REVIEWERS = {ROLE_PLATFORM_ADMIN, ROLE_REVIEWER}
ADMINS = {ROLE_PLATFORM_ADMIN}
WORKFLOW_RULES = (
    ("crear diseño", DesignBriefViewSet, "create", DESIGN_CREATORS),
    ("generar prompt", DesignBriefViewSet, "generate_prompt", DESIGN_CREATORS),
    ("confirmar diseño", DesignBriefViewSet, "confirm_design", DESIGN_CREATORS),
    ("pedir cambios", DesignViewSet, "revise", DESIGN_CREATORS),
    ("subir logos", UploadedLogoViewSet, "create", DESIGN_CREATORS),
    ("crear school-kit", MaterialBundleViewSet, "create", DESIGN_CREATORS),
    ("generar school-kit", MaterialBundleViewSet, "generate", DESIGN_CREATORS),
    ("ejecutar revisión automática", DesignViewSet, "claude_review", DESIGN_CREATORS),
    ("agregar comentarios", DesignViewSet, "comments", HUMAN_REVIEWERS),
    ("aprobar o rechazar", DesignViewSet, "review", HUMAN_REVIEWERS),
    ("reabrir una decision", DesignViewSet, "reopen_review", HUMAN_REVIEWERS),
    ("administrar tipos de material", MaterialTypeViewSet, "create", ADMINS),
    ("administrar plantillas", MaterialTemplateViewSet, "create", ADMINS),
    ("administrar materiales", MarketingAssetViewSet, "create", ADMINS),
)


def _role_user(role):
    user = get_user_model().objects.create_user(
        username=f"{role}-matrix",
        email=f"{role}@ihmexico.com",
        password="RoleMatrix-2026!",
    )
    user.groups.add(Group.objects.get_or_create(name=role)[0])
    return user


@pytest.mark.django_db
@pytest.mark.parametrize(("label", "viewset", "action", "allowed_roles"), WORKFLOW_RULES)
@pytest.mark.parametrize("role", CORPORATE_ROLES)
def test_workflow_actions_enforce_the_documented_role_matrix(
    label, viewset, action, allowed_roles, role
):
    del label
    assert set(viewset.role_rules[action]) == allowed_roles
    request = SimpleNamespace(user=_role_user(role))
    view = SimpleNamespace(action=action, role_rules=viewset.role_rules)

    assert RolePermission().has_permission(request, view) is (role in allowed_roles)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/branding/tokens/",
        "/api/v1/branding/logos/",
        "/api/v1/material-types/",
        "/api/v1/material-templates/",
        "/api/v1/marketing-assets/",
    ],
)
def test_read_only_public_catalogs_remain_available_without_a_session(path):
    assert APIClient().get(path).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("role", CORPORATE_ROLES)
def test_only_platform_admin_can_open_user_administration(role):
    client = APIClient()
    client.force_authenticate(_role_user(role))

    response = client.get("/api/v1/security/users/")

    assert response.status_code == (200 if role == ROLE_PLATFORM_ADMIN else 403)


def test_viewer_role_has_no_mutating_workflow_capability():
    for _label, _viewset, _action, allowed_roles in WORKFLOW_RULES:
        assert ROLE_VIEWER not in allowed_roles
