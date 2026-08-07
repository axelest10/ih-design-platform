#!/usr/bin/env python3
"""Build the versioned artwork-reference catalog from a Drive inventory export.

The inventory is collected from the shared Drive folder. This script only
normalizes metadata; it does not approve artwork and does not download files.
Images are prepared for repository storage, while videos remain source-only by
default so a large binary collection is not copied accidentally.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

COUNTRY_SLUGS = {
    "Chile": "chile",
    "Colombia": "colombia",
    "IELTS LATAM": "ielts-latam",
    "México": "mexico",
    "Perú": "peru",
}


def slugify(value: str) -> str:
    value = value.lower()
    value = value.replace("á", "a").replace("é", "e").replace("í", "i")
    value = value.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "artwork"


def clean_name(name: str) -> str:
    return re.sub(r"\s+(Image|Video)$", "", name, flags=re.IGNORECASE).strip()


def file_extension(name: str) -> str:
    suffix = Path(name).suffix.lower().lstrip(".")
    return suffix or "bin"


def build_entry(file_data: dict, source_folder_url: str, crawled_at: str) -> dict:
    name = clean_name(file_data["name"])
    country = file_data["country"]
    country_slug = COUNTRY_SLUGS.get(country, slugify(country))
    extension = file_extension(name)
    kind = file_data.get("kind", "other")
    local_name = f"{slugify(Path(name).stem)}--{file_data['id']}.{extension}"
    local_file = (
        f"brand/assets/artwork-references/{country_slug}/{local_name}"
        if kind == "image"
        else ""
    )
    path_parts = file_data["folderPath"].split("/")
    tags = ["drive", "artwork", kind, country_slug]
    if len(path_parts) > 1:
        tags.append(slugify(path_parts[-1]))
    return {
        "key": f"drive-artwork-{file_data['id']}",
        "title": name,
        "reference_type": "inspiration",
        "approval_status": "pending",
        "file": local_file,
        "source_url": f"https://drive.google.com/file/d/{file_data['id']}/view",
        "source_folder_url": f"https://drive.google.com/drive/folders/{file_data['parentId']}",
        "source_file_name": name,
        "brand_scope": "international-house-latam",
        "country": country_slug,
        "product_slug": "",
        "format": extension,
        "tags": tags,
        "usage_notes": (
            "Referencia visual; requiere revisión humana antes de reutilizar, adaptar o publicar."
        ),
        "provenance": {
            "source_folder_id": file_data["parentId"],
            "source_path": file_data["folderPath"],
            "source_kind": kind,
            "crawled_at": crawled_at,
        },
    }


def build_catalog(inventory: dict) -> tuple[dict, list[dict]]:
    source_url = inventory["sourceFolderUrl"]
    crawled_at = inventory["crawledAt"]
    entries = [
        build_entry(item, source_url, crawled_at) for item in inventory["files"]
    ]
    entries.sort(key=lambda entry: (entry["country"], entry["source_file_name"].lower()))
    catalog = {
        "version": "1.0.0",
        "status": "pending-review",
        "source": {
            "type": "google-drive-shared-folder",
            "folder_url": source_url,
            "crawled_at": crawled_at,
        },
        "policy": {
            "reference_type": "inspiration",
            "approval_status": "pending",
            "images": "copied-to-repository",
            "videos": "source-only-until-storage-policy-is-confirmed",
            "note": "No item is approved solely because it was present in Drive.",
        },
        "folders": inventory["folders"],
        "entries": entries,
    }
    download_plan = [
        {
            "id": entry["key"].removeprefix("drive-artwork-"),
            "source_url": entry["source_url"],
            "target": entry["file"],
        }
        for entry in entries
        if entry["file"]
    ]
    return catalog, download_plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--download-plan", type=Path)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    catalog, download_plan = build_catalog(inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    if args.download_plan:
        args.download_plan.write_text(
            json.dumps(download_plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
