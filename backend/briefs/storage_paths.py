"""User-scoped storage paths for brief uploads."""

from pathlib import PurePath


def _safe_filename(filename: str) -> str:
    return PurePath(str(filename).replace("\\", "/")).name


def brief_reference_path(instance, filename: str) -> str:
    owner_id = instance.created_by_id or "unassigned"
    return f"users/{owner_id}/brief-references/{_safe_filename(filename)}"
