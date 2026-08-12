from django.urls import include, path
from rest_framework.routers import DefaultRouter

from assets.views import ArtworkReferenceViewSet, OfficialAssetViewSet, UploadedLogoViewSet
from branding.views import BrandGuidelineViewSet, brand_logos, brand_tokens, validate_color
from briefs.views import BriefReferenceUploadViewSet, DesignBriefViewSet
from campaigns.views import CampaignViewSet
from catalog.views import BranchViewSet, ProductViewSet
from common.views import stats_summary
from designs.views import DesignViewSet
from materials.views import (
    MarketingAssetViewSet,
    MaterialBundleViewSet,
    MaterialTemplateViewSet,
    MaterialTypeViewSet,
    quick_design,
)
from security.admin_views import (
    corporate_user_detail,
    corporate_user_list,
    corporate_user_password,
    corporate_user_roles,
)
from security.views import (
    change_password,
    confirm_password_reset,
    current_user,
    password_login,
    request_password_reset,
    session_logout,
)
from validations.views import ValidationRunViewSet

router = DefaultRouter()
router.register("branding", BrandGuidelineViewSet, basename="branding")
router.register("products", ProductViewSet, basename="products")
router.register("branches", BranchViewSet, basename="branches")
router.register("campaigns", CampaignViewSet, basename="campaigns")
router.register("briefs", DesignBriefViewSet, basename="briefs")
router.register("designs", DesignViewSet, basename="designs")
router.register("assets", OfficialAssetViewSet, basename="assets")
router.register("uploaded-logos", UploadedLogoViewSet, basename="uploaded-logo")
router.register("artwork-references", ArtworkReferenceViewSet, basename="artwork-reference")
router.register(
    "brief-reference-uploads",
    BriefReferenceUploadViewSet,
    basename="brief-reference-upload",
)
router.register("validations", ValidationRunViewSet, basename="validations")
router.register("material-types", MaterialTypeViewSet, basename="material-type")
router.register("material-templates", MaterialTemplateViewSet, basename="material-template")
router.register("material-bundles", MaterialBundleViewSet, basename="material-bundle")
router.register("marketing-assets", MarketingAssetViewSet, basename="marketing-asset")

urlpatterns = [
    path(
        "designs/<int:pk>/versions/<int:version_number>/export/",
        DesignViewSet.as_view({"get": "export_version"}),
        name="design-version-export",
    ),
    path("materials/quick-design/", quick_design, name="materials-quick-design"),
    path(
        "materials/marketing-assets/bulk/",
        MarketingAssetViewSet.as_view({"post": "bulk"}),
        name="materials-marketing-assets-bulk",
    ),
    path(
        "marketing-assets/<int:pk>/file/<str:filename>",
        MarketingAssetViewSet.as_view({"get": "file"}),
        name="marketing-asset-file",
    ),
    path("stats/summary/", stats_summary, name="stats-summary"),
    path("security/users/", corporate_user_list, name="security-user-list"),
    path(
        "security/users/<int:user_id>/roles/",
        corporate_user_roles,
        name="security-user-roles",
    ),
    path(
        "security/users/<int:user_id>/",
        corporate_user_detail,
        name="security-user-detail",
    ),
    path(
        "security/users/<int:user_id>/password/",
        corporate_user_password,
        name="security-user-password",
    ),
    path("auth/login/", password_login, name="password-login"),
    path("auth/logout/", session_logout, name="session-logout"),
    path(
        "auth/password-reset/request/",
        request_password_reset,
        name="password-reset-request",
    ),
    path(
        "auth/password-reset/confirm/",
        confirm_password_reset,
        name="password-reset-confirm",
    ),
    path("auth/change-password/", change_password, name="change-password"),
    path("me/", current_user),
    # Rutas explícitas de branding basadas en archivos (brand/) — deben ir antes del router
    # para no chocar con el patrón branding/<pk>/ del ModelViewSet.
    path("branding/tokens/", brand_tokens),
    path("branding/logos/", brand_logos),
    path("branding/validate-color/", validate_color),
    path("", include(router.urls)),
]
