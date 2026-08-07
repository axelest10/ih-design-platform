#!/usr/bin/env python3
"""
brand/scripts/generate_product_catalog.py

Genera brand/knowledge/product-catalog.json a partir de
brand/knowledge/product-catalog.yaml, que es la ÚNICA fuente de verdad.

NO editar a mano:
  - brand/knowledge/product-catalog.json

Uso:
    python brand/scripts/generate_product_catalog.py
    python brand/scripts/generate_product_catalog.py --check   # falla si quedó desactualizado
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

BRAND_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BRAND_DIR / "knowledge"
SOURCE_YAML = KNOWLEDGE_DIR / "product-catalog.yaml"
OUTPUT_JSON = KNOWLEDGE_DIR / "product-catalog.json"

GENERATED_HEADER = (
    "Generado automáticamente por brand/scripts/generate_product_catalog.py. "
    "No editar a mano — editar brand/knowledge/product-catalog.yaml."
)


def load_source() -> dict:
    with SOURCE_YAML.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def build_json(source: dict) -> dict:
    products = source.get("products", [])
    deprecated = source.get("deprecated", [])
    by_status = {}
    for product in products:
        status = product.get("status", "needs_confirmation")
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "$schema": "generated-by-generate_product_catalog.py",
        "$comment": GENERATED_HEADER,
        "version": source.get("version"),
        "status": source.get("status"),
        "countries": source.get("countries", {}),
        "regional_groups": source.get("regional_groups", {}),
        "summary": {
            "total_products": len(products),
            "by_status": by_status,
            "total_deprecated": len(deprecated),
        },
        "products": products,
        "deprecated": deprecated,
    }


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="No escribir; falla si algo está desactualizado."
    )
    args = parser.parse_args()

    source = load_source()
    output_text = json.dumps(build_json(source), ensure_ascii=False, indent=2) + "\n"

    if args.check:
        current = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else None
        if current != output_text:
            print(f"Archivo generado desactualizado: {OUTPUT_JSON}")
            return 1
        print("product-catalog.json está al día.")
        return 0

    if write_if_changed(OUTPUT_JSON, output_text):
        print(f"Archivo generado/actualizado: {OUTPUT_JSON}")
    else:
        print("Sin cambios — product-catalog.json ya estaba al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
