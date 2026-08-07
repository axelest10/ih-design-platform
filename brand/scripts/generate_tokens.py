#!/usr/bin/env python3
"""
brand/scripts/generate_tokens.py

Genera los artefactos técnicos de la marca IH México a partir de los YAML en
brand/tokens/ y brand/product-colors/, que son la ÚNICA fuente de verdad.

NO editar a mano:
  - brand/tokens/colors.json
  - brand/generated/ih-brand.css
  - brand/generated/tokens.js
  - brand/generated/tailwind-preset.js

Uso:
    python brand/scripts/generate_tokens.py
    python brand/scripts/generate_tokens.py --check   # falla si hay archivos desactualizados
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

BRAND_DIR = Path(__file__).resolve().parent.parent
TOKENS_DIR = BRAND_DIR / "tokens"
PRODUCT_COLORS_DIR = BRAND_DIR / "product-colors"
GENERATED_DIR = BRAND_DIR / "generated"

GENERATED_HEADER = (
    "Generado automáticamente por brand/scripts/generate_tokens.py.\n"
    "No editar a mano — editar los YAML fuente en brand/tokens/ y brand/product-colors/."
)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_all_tokens() -> dict:
    return {
        "colors": load_yaml(TOKENS_DIR / "colors.yaml"),
        "typography": load_yaml(TOKENS_DIR / "typography.yaml"),
        "spacing": load_yaml(TOKENS_DIR / "spacing.yaml"),
        "radius": load_yaml(TOKENS_DIR / "radius.yaml"),
        "shadows": load_yaml(TOKENS_DIR / "shadows.yaml"),
        "motion": load_yaml(TOKENS_DIR / "motion.yaml"),
        "product_colors": load_yaml(PRODUCT_COLORS_DIR / "authorized-colors.yaml"),
    }


def flat_color_map(tokens: dict) -> dict:
    """Mapa plano {token_name: hex} combinando paleta primaria, secundaria y extensiones."""
    colors = tokens["colors"]
    flat = {}
    for group in ("primary_palette", "secondary_palette"):
        for name, data in colors.get(group, {}).items():
            flat[name] = data["hex"]
    for name, data in colors.get("extended_colors", {}).items():
        flat[name] = data["hex"]
    for name, data in colors.get("neutrals", {}).items():
        flat[f"neutral_{name}"] = data["hex"]
    return flat


def build_colors_json(tokens: dict) -> dict:
    colors = tokens["colors"]
    return {
        "$schema": "generated-by-generate_tokens.py",
        "version": colors.get("version"),
        "status": colors.get("status"),
        "source_of_truth": colors.get("source_of_truth"),
        "primary_palette": colors.get("primary_palette"),
        "secondary_palette": colors.get("secondary_palette"),
        "extended_colors": colors.get("extended_colors"),
        "neutrals": colors.get("neutrals"),
        "rainbow": colors.get("rainbow"),
        "product_colors": tokens["product_colors"].get("pillars"),
    }


def css_var_name(name: str) -> str:
    return "--ih-" + name.replace("_", "-")


def build_css(tokens: dict) -> str:
    flat = flat_color_map(tokens)
    typography = tokens["typography"]
    spacing = tokens["spacing"]
    radius = tokens["radius"]
    shadows = tokens["shadows"]
    motion = tokens["motion"]
    product_colors = tokens["product_colors"].get("pillars", {})

    lines = [f"/* {GENERATED_HEADER} */", "", ":root {", "  /* Colores institucionales */"]
    for name, hex_value in flat.items():
        lines.append(f"  {css_var_name(name)}: {hex_value};")

    lines.append("")
    lines.append("  /* Colores por pilar/producto (ver brand/product-colors/) */")
    for slug, data in product_colors.items():
        slug_css = slug.replace("_", "-")
        lines.append(f"  --ih-pillar-{slug_css}-primary: {data['primary_hex']};")
        lines.append(f"  --ih-pillar-{slug_css}-secondary: {data['secondary_hex']};")
        lines.append(f"  --ih-pillar-{slug_css}-background: {data['background_hex']};")
        lines.append(f"  --ih-pillar-{slug_css}-cta-bg: {data['cta']['background_hex']};")
        lines.append(f"  --ih-pillar-{slug_css}-cta-text: {data['cta']['text_hex']};")

    lines.append("")
    lines.append("  /* Tipografía */")
    lines.append(f"  --ih-font-heading: {typography['typefaces']['heading']['fallback_stack']};")
    lines.append(f"  --ih-font-body: {typography['typefaces']['body']['fallback_stack']};")
    for style_name, style in typography["type_scale"]["styles"].items():
        css_name = style_name.replace("_", "-")
        if "size_px" in style:
            lines.append(f"  --ih-type-{css_name}-size: {style['size_px']}px;")
        if "line_height_px" in style:
            lines.append(f"  --ih-type-{css_name}-line-height: {style['line_height_px']}px;")

    lines.append("")
    lines.append("  /* Espaciado */")
    for name, value in spacing["scale"].items():
        lines.append(f"  --ih-space-{name}: {value}px;")

    lines.append("")
    lines.append("  /* Radios */")
    for name, value in radius["values"].items():
        css_name = name.replace("_px", "").replace("_", "-")
        lines.append(f"  --ih-radius-{css_name}: {value}px;")

    lines.append("")
    lines.append("  /* Sombras */")
    for name, value in shadows["values"].items():
        css_name = name.replace("_", "-")
        lines.append(f"  --ih-shadow-{css_name}: {value};")

    lines.append("")
    lines.append(f"  /* Motion — {motion['status']}, NO usar como regla de marca aprobada */")
    for name, value in motion["durations_ms"].items():
        lines.append(f"  --ih-motion-duration-{name}: {value}ms;")
    for name, value in motion["easing"].items():
        lines.append(f"  --ih-motion-easing-{name}: {value};")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def build_tokens_js(tokens: dict) -> str:
    payload = {
        "colors": flat_color_map(tokens),
        "productColors": tokens["product_colors"].get("pillars"),
        "typography": tokens["typography"],
        "spacing": tokens["spacing"],
        "radius": tokens["radius"]["values"],
        "shadows": tokens["shadows"]["values"],
        "motion": tokens["motion"],
        "rainbow": tokens["colors"].get("rainbow"),
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        f"/* {GENERATED_HEADER} */\n\n"
        f"export const ihBrandTokens = {body};\n\n"
        "export default ihBrandTokens;\n"
    )


def build_tailwind_preset(tokens: dict) -> str:
    flat = flat_color_map(tokens)
    product_colors = tokens["product_colors"].get("pillars", {})
    spacing = tokens["spacing"]["scale"]
    radius = tokens["radius"]["values"]
    boxshadow = tokens["shadows"]["values"]
    typography = tokens["typography"]

    color_entries = ",\n".join(f'        {name}: "{hex_value}"' for name, hex_value in flat.items())
    pillar_entries = []
    for slug, data in product_colors.items():
        js_key = slug.replace("_", "-")
        pillar_entries.append(
            f'        "{js_key}": {{\n'
            f'          DEFAULT: "{data["primary_hex"]}",\n'
            f'          secondary: "{data["secondary_hex"]}",\n'
            f'          background: "{data["background_hex"]}"\n'
            f"        }}"
        )
    pillar_block = ",\n".join(pillar_entries)

    spacing_entries = ",\n".join(
        f'        "{name}": "{value}px"' for name, value in spacing.items()
    )
    radius_entries = ",\n".join(
        f'        "{name.replace("_px", "").replace("_", "-")}": "{value}px"'
        for name, value in radius.items()
    )
    shadow_entries = ",\n".join(
        f'        "{name}": "{value}"' for name, value in boxshadow.items()
    )

    return f"""/* {GENERATED_HEADER} */

/** @type {{import('tailwindcss').Config}} */
module.exports = {{
  theme: {{
    extend: {{
      colors: {{
{color_entries},
        pillar: {{
{pillar_block}
        }}
      }},
      fontFamily: {{
        heading: ["{typography['typefaces']['heading']['name']}", "Arial", "sans-serif"],
        body: ["{typography['typefaces']['body']['name']}", "sans-serif"]
      }},
      spacing: {{
{spacing_entries}
      }},
      borderRadius: {{
{radius_entries}
      }},
      boxShadow: {{
{shadow_entries}
      }}
    }}
  }}
}};
"""


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

    tokens = load_all_tokens()

    colors_json_text = json.dumps(build_colors_json(tokens), ensure_ascii=False, indent=2) + "\n"
    outputs = {
        TOKENS_DIR / "colors.json": colors_json_text,
        GENERATED_DIR / "ih-brand.css": build_css(tokens),
        GENERATED_DIR / "tokens.js": build_tokens_js(tokens),
        GENERATED_DIR / "tailwind-preset.js": build_tailwind_preset(tokens),
    }

    if args.check:
        stale = []
        for path, content in outputs.items():
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != content:
                stale.append(str(path))
        if stale:
            print("Archivos generados desactualizados:", *stale, sep="\n  - ")
            return 1
        print("Todos los archivos generados están al día.")
        return 0

    changed = []
    for path, content in outputs.items():
        if write_if_changed(path, content):
            changed.append(str(path))

    if changed:
        print("Archivos generados/actualizados:", *changed, sep="\n  - ")
    else:
        print("Sin cambios — todos los archivos generados ya estaban al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
