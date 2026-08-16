"""User-scoped storage paths for uploaded asset files."""

from pathlib import PurePath


def _safe_filename(filename: str) -> str:
    return PurePath(str(filename).replace("\\", "/")).name


def uploaded_logo_path(instance, filename: str) -> str:
    owner_id = instance.created_by_id or "unassigned"
    return f"users/{owner_id}/uploaded-logos/{_safe_filename(filename)}"
