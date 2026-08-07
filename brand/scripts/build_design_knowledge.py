#!/usr/bin/env python3
"""Generate the machine-readable visual knowledge base from the artwork manifest.

The output is intentionally metadata-first. It records observable facts about
the repository files and their provenance, while leaving semantic design
annotations explicit as pending instead of guessing them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import yaml
from PIL import Image

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observed_palette(path: Path) -> list[dict]:
    with Image.open(path) as image:
        sample = image.convert("RGB").resize((64, 64))
        quantized = sample.quantize(colors=8)
        palette = quantized.getpalette()
        colors = sorted(quantized.getcolors() or [], reverse=True)
    total = sum(count for count, _ in colors) or 1
    result = []
    for count, index in colors[:8]:
        red, green, blue = palette[index * 3 : index * 3 + 3]
        result.append(
            {
                "hex": f"#{red:02X}{green:02X}{blue:02X}",
                "share": round(count / total, 4),
            }
        )
    return result


def calendar_context(source_path: str) -> dict:
    year_match = re.search(r"20\d{2}", source_path)
    normalized = source_path.lower()
    month_name = next((name for name in MONTHS if name in normalized), None)
    return {
        "year": int(year_match.group()) if year_match else None,
        "month": MONTHS.get(month_name) if month_name else None,
        "month_name": month_name,
    }


def dimensions(path: Path) -> dict:
    with Image.open(path) as image:
        width, height = image.size
    ratio = round(width / height, 4) if height else None
    orientation = "square" if ratio == 1 else ("landscape" if ratio > 1 else "portrait")
    return {
        "width": width,
        "height": height,
        "aspect_ratio": ratio,
        "orientation": orientation,
    }


ANNOTATION_TOP_LEVEL_FIELDS = (
    "product_slug",
    "content_pillar",
    "campaign_or_theme",
    "annotation_status",
)

ANNOTATION_NESTED_FIELDS = (
    "product_status",
    "audience",
    "funnel_stage",
    "visual_tags",
    "background_type",
    "composition_type",
    "layout_pattern",
    "image_subject",
    "people_count",
    "logo_present",
    "logo_placement",
    "logo_variant",
    "logo_scale",
    "headline_present",
    "headline_treatment",
    "supporting_text_present",
    "cta_present",
    "cta_treatment",
    "typography_style",
    "photo_style",
    "graphic_elements",
    "recommended_use",
    "annotation_confidence",
    "annotation_source",
    "needs_review",
    "review_note",
)


def load_annotations(path: Path) -> dict:
    if not path.exists():
        return {"default_annotation": {}, "heuristic_rules": [], "overrides": {}}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {
        "default_annotation": data.get("default_annotation", {}),
        "heuristic_rules": data.get("heuristic_rules", []),
        "overrides": data.get("overrides", {}),
    }


def _rule_matches(
    condition: dict, entry: dict, asset_country: str, orientation: str | None
) -> bool:
    # "tag_contains" busca en tags Y en el título/ruta de origen, porque los tags automáticos
    # del manifest son genéricos (país/mes) y las palabras clave de producto (p. ej. "ielts")
    # normalmente solo aparecen en el nombre del archivo o de la carpeta de Drive.
    haystack = " ".join(
        [
            str(entry.get("title", "")),
            str(entry.get("provenance", {}).get("source_path", "")),
            *[str(t) for t in entry.get("tags", [])],
        ]
    ).lower()
    if "tag_contains" in condition:
        needle = str(condition["tag_contains"]).lower()
        if needle not in haystack:
            return False
    if "country" in condition and condition["country"] != asset_country:
        return False
    if "country_not" in condition and condition["country_not"] == asset_country:
        return False
    if "orientation" in condition and condition["orientation"] != orientation:
        return False
    return True


def resolve_annotation(
    entry: dict, asset_id: str, asset_country: str, orientation: str | None, annotations: dict
) -> dict:
    """Combina default_annotation -> heuristic_rules (en orden) -> overrides[asset_id]."""
    merged = dict(annotations["default_annotation"])
    for rule in annotations["heuristic_rules"]:
        if _rule_matches(rule.get("when", {}), entry, asset_country, orientation):
            merged.update(rule.get("apply", {}))
    override = annotations["overrides"].get(asset_id)
    if override:
        merged.update(override)
    return merged


def build_asset(entry: dict, repo_root: Path, annotations: dict) -> dict:
    repository_path = entry.get("file", "")
    local_path = repo_root / repository_path if repository_path else None
    media_type = entry["provenance"].get("source_kind", "unknown")
    asset_country = entry.get("country", "")
    asset = {
        "id": entry["key"],
        "title": entry["title"],
        "media_type": media_type,
        "format": entry.get("format", ""),
        "country": asset_country,
        "calendar": calendar_context(entry["provenance"].get("source_path", "")),
        "collection_path": entry["provenance"].get("source_path", ""),
        "tags": entry.get("tags", []),
        "source": {
            "file_name": entry.get("source_file_name", ""),
            "file_url": entry.get("source_url", ""),
            "folder_url": entry.get("source_folder_url", ""),
            "folder_id": entry.get("provenance", {}).get("source_folder_id", ""),
        },
        "repository": {
            "path": repository_path,
            "available": bool(local_path and local_path.exists()),
        },
        "review": {
            "reference_type": entry.get("reference_type", "inspiration"),
            "approval_status": entry.get("approval_status", "pending"),
            "inspiration_only": True,
            "requires_human_approval": True,
        },
        "visual_analysis": {
            "status": "metadata-only",
            "semantic_fields_pending": [
                "headline_treatment",
                "logo_placement",
                "subject_type",
                "composition",
                "cta_treatment",
                "typography_style",
            ],
        },
    }
    orientation = None
    if local_path and local_path.exists():
        asset["repository"].update(
            {
                "bytes": local_path.stat().st_size,
                "sha256": sha256(local_path),
            }
        )
        try:
            dims = dimensions(local_path)
            orientation = dims.get("orientation")
            asset["technical"] = {
                **dims,
                "observed_palette": observed_palette(local_path),
                "palette_note": "Colores observados en píxeles; no son tokens oficiales.",
            }
        except (OSError, ValueError):
            asset["technical"] = {"analysis_error": "image-metadata-unavailable"}
    else:
        asset["technical"] = {"availability_note": "source-only; binary not copied"}

    merged = resolve_annotation(entry, entry["key"], asset_country, orientation, annotations)
    for field in ANNOTATION_TOP_LEVEL_FIELDS:
        asset[field] = merged.get(field)
    asset["review"]["reuse_permission"] = merged.get(
        "reuse_permission", "client-authorized-reuse"
    )
    asset["annotation"] = {field: merged.get(field) for field in ANNOTATION_NESTED_FIELDS}
    return asset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--annotations",
        type=Path,
        default=None,
        help=(
            "Ruta a artwork-annotations.yaml. Por defecto "
            "brand/knowledge/artwork-annotations.yaml junto al output."
        ),
    )
    args = parser.parse_args()

    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8")) or {}
    repo_root = args.manifest.parents[3]
    default_annotations_path = (
        Path(__file__).resolve().parent.parent / "knowledge" / "artwork-annotations.yaml"
    )
    annotations_path = args.annotations or default_annotations_path
    annotations = load_annotations(annotations_path)

    assets = [build_asset(entry, repo_root, annotations) for entry in manifest["entries"]]
    counts = Counter(asset["media_type"] for asset in assets)
    countries = Counter(asset["country"] for asset in assets)
    annotation_statuses = Counter(asset["annotation_status"] for asset in assets)
    product_slugs = Counter(asset["product_slug"] for asset in assets if asset["product_slug"])
    needs_review_count = sum(1 for asset in assets if asset["annotation"].get("needs_review"))
    knowledge = {
        "schema": "ih-design-visual-knowledge",
        "schema_version": "1.1.0",
        "generated_from": (
            "brand/assets/artwork-references/manifest.yaml + "
            "brand/knowledge/artwork-annotations.yaml"
        ),
        "purpose": "Selección trazable de referencias visuales para nuevos diseños.",
        "guardrails": [
            "Usar como inspiración y evidencia de precedentes, no como aprobación automática.",
            "No inferir reglas oficiales de marca desde una pieza individual.",
            "Confirmar país, producto, derechos y revisión humana antes de publicar.",
            "Los colores observados son metadata de imagen y no reemplazan tokens autorizados.",
            "reuse_permission=client-authorized-reuse no cambia review.approval_status ni "
            "reemplaza la revisión humana pieza por pieza.",
        ],
        "source": manifest["source"],
        "summary": {
            "total_assets": len(assets),
            "by_media_type": dict(sorted(counts.items())),
            "by_country": dict(sorted(countries.items())),
            "local_binaries": sum(asset["repository"]["available"] for asset in assets),
            "by_annotation_status": dict(sorted(annotation_statuses.items())),
            "by_product_slug": dict(sorted(product_slugs.items())),
            "needs_review": needs_review_count,
        },
        "selection_dimensions": [
            "country",
            "calendar.year",
            "calendar.month",
            "media_type",
            "format",
            "technical.orientation",
            "technical.aspect_ratio",
            "tags",
            "review.approval_status",
            "product_slug",
            "content_pillar",
            "campaign_or_theme",
            "annotation_status",
        ],
        "assets": assets,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(knowledge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
