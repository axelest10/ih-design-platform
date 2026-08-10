from django.conf import settings
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.static import serve

from common.views import health

frontend_root = settings.BASE_DIR / "frontend"
brand_assets_root = settings.BASE_DIR / "brand" / "assets"
brand_generated_root = settings.BASE_DIR / "brand" / "generated"

urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("api_urls")),
]

urlpatterns += [
    path("", TemplateView.as_view(template_name="index.html"), name="frontend-home"),
    path("login.html", TemplateView.as_view(template_name="login.html"), name="frontend-login"),
    path("panel.html", TemplateView.as_view(template_name="panel.html"), name="frontend-panel"),
    path("review.html", TemplateView.as_view(template_name="review.html"), name="frontend-review"),
    path(
        "school-kit.html",
        TemplateView.as_view(template_name="school-kit.html"),
        name="frontend-school-kit",
    ),
    path("admin.html", TemplateView.as_view(template_name="admin.html"), name="frontend-admin"),
    path(
        "styles/<path:path>",
        serve,
        {"document_root": frontend_root / "styles"},
        name="frontend-styles",
    ),
    path(
        "scripts/<path:path>",
        serve,
        {"document_root": frontend_root / "scripts"},
        name="frontend-scripts",
    ),
    path(
        "brand/assets/<path:path>",
        serve,
        {"document_root": brand_assets_root},
        name="brand-assets",
    ),
    path(
        "brand/generated/<path:path>",
        serve,
        {"document_root": brand_generated_root},
        name="brand-generated",
    ),
]
