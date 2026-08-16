"""User-scoped storage paths for marketing asset files."""

from pathlib import PurePath


def _safe_filename(filename: str) -> str:
    return PurePath(str(filename).replace("\\", "/")).name


def marketing_asset_path(instance, filename: str) -> str:
    owner_id = instance.uploaded_by_id or "unassigned"
    return f"users/{owner_id}/marketing-assets/{_safe_filename(filename)}"
