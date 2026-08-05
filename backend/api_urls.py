from django.urls import include, path
from rest_framework.routers import DefaultRouter

from assets.views import OfficialAssetViewSet
from branding.views import BrandGuidelineViewSet
from briefs.views import DesignBriefViewSet
from campaigns.views import CampaignViewSet
from catalog.views import BranchViewSet, ProductViewSet
from common.views import health
from designs.views import DesignViewSet
from validations.views import ValidationRunViewSet

router = DefaultRouter()
router.register("branding", BrandGuidelineViewSet, basename="branding")
router.register("products", ProductViewSet, basename="products")
router.register("branches", BranchViewSet, basename="branches")
router.register("campaigns", CampaignViewSet, basename="campaigns")
router.register("briefs", DesignBriefViewSet, basename="briefs")
router.register("designs", DesignViewSet, basename="designs")
router.register("assets", OfficialAssetViewSet, basename="assets")
router.register("validations", ValidationRunViewSet, basename="validations")

urlpatterns = [path("health/", health), path("", include(router.urls))]
