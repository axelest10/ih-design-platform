from django.urls import include, path
from rest_framework.routers import DefaultRouter

from assets.views import ArtworkReferenceViewSet, OfficialAssetViewSet, UploadedLogoViewSet
from branding.views import BrandGuidelineViewSet, brand_logos, brand_tokens, validate_color
from briefs.views import BriefReferenceUploadViewSet, DesignBriefViewSet
from campaigns.views import CampaignViewSet
from catalog.views import BranchViewSet, ProductViewSet
from common.views import stats_summary
from designs.views import DesignViewSet
from materials.views import MaterialBundleViewSet, MaterialTemplateViewSet, MaterialTypeViewSet
from security.admin_views import corporate_user_detail, corporate_user_list, corporate_user_roles
from security.views import current_user, site_access
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

urlpatterns = [
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
    path("auth/site-access/", site_access, name="site-access"),
    path("me/", current_user),
    # Rutas explícitas de branding basadas en archivos (brand/) — deben ir antes del router
    # para no chocar con el patrón branding/<pk>/ del ModelViewSet.
    path("branding/tokens/", brand_tokens),
    path("branding/logos/", brand_logos),
    path("branding/validate-color/", validate_color),
    path("", include(router.urls)),
]
