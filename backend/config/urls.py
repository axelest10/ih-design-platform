from django.conf import settings
from django.urls import include, path

from common.frontend_views import (
    HubAuthenticatedTemplateView,
    RevalidatedTemplateView,
    serve_brand_asset,
    serve_revalidated_file,
    serve_versioned_asset,
)
from common.views import health

frontend_root = settings.BASE_DIR / "frontend"
brand_assets_root = settings.BASE_DIR / "brand" / "assets"
brand_generated_root = settings.BASE_DIR / "brand" / "generated"
brand_documentation_root = settings.BASE_DIR / "brand" / "documentation"

urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("api_urls")),
]

urlpatterns += [
    path("", RevalidatedTemplateView.as_view(template_name="index.html"), name="frontend-home"),
    path(
        "index.html",
        RevalidatedTemplateView.as_view(template_name="index.html"),
        name="frontend-home-index",
    ),
    path(
        "login.html",
        RevalidatedTemplateView.as_view(
            template_name="login.html",
            extra_context={"hub_oidc_enabled": settings.HUB_OIDC_ENABLED},
        ),
        name="frontend-login",
    ),
    path(
        "catalog.html",
        RevalidatedTemplateView.as_view(template_name="catalog.html"),
        name="frontend-catalog",
    ),
    path(
        "templates-gallery.html",
        RevalidatedTemplateView.as_view(template_name="templates-gallery.html"),
        name="frontend-templates-gallery",
    ),
    path(
        "marketing-materials.html",
        HubAuthenticatedTemplateView.as_view(template_name="marketing-materials.html"),
        name="frontend-marketing-materials",
    ),
    path(
        "brand-rules.html",
        RevalidatedTemplateView.as_view(template_name="brand-rules.html"),
        name="frontend-brand-rules",
    ),
    path(
        "panel.html",
        HubAuthenticatedTemplateView.as_view(template_name="panel.html"),
        name="frontend-panel",
    ),
    path(
        "review.html",
        HubAuthenticatedTemplateView.as_view(template_name="review.html"),
        name="frontend-review",
    ),
    path(
        "school-kit.html",
        HubAuthenticatedTemplateView.as_view(template_name="school-kit.html"),
        name="frontend-school-kit",
    ),
    path(
        "admin.html",
        HubAuthenticatedTemplateView.as_view(template_name="admin.html"),
        name="frontend-admin",
    ),
    path(
        "styles/<path:path>",
        serve_versioned_asset,
        {"document_root": frontend_root / "styles"},
        name="frontend-styles",
    ),
    path(
        "scripts/<path:path>",
        serve_versioned_asset,
        {"document_root": frontend_root / "scripts"},
        name="frontend-scripts",
    ),
    path(
        "brand/assets/<path:path>",
        serve_brand_asset,
        {"document_root": brand_assets_root},
        name="brand-assets",
    ),
    path(
        "brand/generated/<path:path>",
        serve_versioned_asset,
        {"document_root": brand_generated_root},
        name="brand-generated",
    ),
    path(
        "brand/documentation/<path:path>",
        serve_revalidated_file,
        {"document_root": brand_documentation_root},
        name="brand-documentation",
    ),
]
