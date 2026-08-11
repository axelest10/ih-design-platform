from pathlib import Path

from django.utils._os import safe_join
from django.utils.cache import patch_cache_control
from django.views.generic import TemplateView
from django.views.static import serve

from .frontend_assets import file_digest


class RevalidatedTemplateView(TemplateView):
    """Serve deploy-sensitive HTML without allowing a stale browser copy."""

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_cache_control(response, no_cache=True, must_revalidate=True, max_age=0)
        return response


def serve_versioned_asset(request, path, document_root):
    response = serve(request, path, document_root=document_root)
    absolute_path = Path(safe_join(document_root, path))
    stat = absolute_path.stat()
    expected_version = file_digest(str(absolute_path), stat.st_mtime_ns, stat.st_size)
    if request.GET.get("v") == expected_version:
        patch_cache_control(response, public=True, max_age=31536000, immutable=True)
    else:
        patch_cache_control(response, no_cache=True, must_revalidate=True, max_age=0)
    return response


def serve_brand_asset(request, path, document_root):
    response = serve(request, path, document_root=document_root)
    patch_cache_control(response, public=True, max_age=86400)
    return response


def serve_revalidated_file(request, path, document_root):
    response = serve(request, path, document_root=document_root)
    patch_cache_control(response, no_cache=True, must_revalidate=True, max_age=0)
    return response
