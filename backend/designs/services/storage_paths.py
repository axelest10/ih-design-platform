"""Storage paths for generated design files."""

from pathlib import PurePath


def _safe_filename(filename: str) -> str:
    return PurePath(str(filename).replace("\\", "/")).name


def generated_design_path(design, filename: str) -> str:
    owner_id = design.brief.created_by_id or "unassigned"
    return f"users/{owner_id}/generated-designs/{design.pk}/{_safe_filename(filename)}"
