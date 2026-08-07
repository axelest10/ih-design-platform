from django.conf import settings
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.static import serve

frontend_root = settings.BASE_DIR / "frontend"
brand_assets_root = settings.BASE_DIR / "brand" / "assets"

urlpatterns = [path("api/v1/", include("api_urls"))]

urlpatterns += [
    path("", TemplateView.as_view(template_name="index.html"), name="frontend-home"),
    path("panel.html", TemplateView.as_view(template_name="panel.html"), name="frontend-panel"),
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
]
