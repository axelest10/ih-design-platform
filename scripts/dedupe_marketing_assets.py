"""Find and optionally delete duplicate MarketingAsset records through the API."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass

try:
    from scripts.bulk_upload_marketing_assets import (
        DEFAULT_BASE_URL,
        MARKETING_ASSETS_PATH,
        UploadError,
        _response_reason,
        authenticated_api_session,
        fetch_all_marketing_assets,
        marketing_asset_key,
    )
except ModuleNotFoundError:
    from bulk_upload_marketing_assets import (  # type: ignore[no-redef]
        DEFAULT_BASE_URL,
        MARKETING_ASSETS_PATH,
        UploadError,
        _response_reason,
        authenticated_api_session,
        fetch_all_marketing_assets,
        marketing_asset_key,
    )


@dataclass(frozen=True)
class DuplicateGroup:
    key: tuple[str, ...]
    keep: dict
    delete: tuple[dict, ...]


def _numeric_id(asset: dict) -> int:
    try:
        return int(asset["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UploadError("Un material recibido no contiene un id numérico válido.") from exc


def find_duplicate_groups(assets: list[dict]) -> list[DuplicateGroup]:
    grouped: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for asset in assets:
        key = marketing_asset_key(
            asset.get("brand", ""),
            asset.get("country", ""),
            asset.get("category", ""),
            asset.get("label", ""),
        )
        grouped[key].append(asset)

    duplicates = []
    for key, items in grouped.items():
        if len(items) < 2:
            continue
        ordered = sorted(items, key=_numeric_id)
        duplicates.append(
            DuplicateGroup(key=key, keep=ordered[0], delete=tuple(ordered[1:]))
        )
    return sorted(duplicates, key=lambda group: (_numeric_id(group.keep), group.key))


def print_deletion_plan(groups: list[DuplicateGroup]) -> None:
    headers = ("Conservar ID", "Borrar ID", "Brand", "País", "Categoría", "Label")
    rows = [
        (
            str(group.keep["id"]),
            str(duplicate["id"]),
            group.key[0],
            group.key[1] or "Global",
            group.key[2],
            group.key[3],
        )
        for group in groups
        for duplicate in group.delete
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        if rows
        else len(headers[index])
        for index in range(len(headers))
    ]

    def line(values: tuple[str, ...]) -> str:
        return " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(values)
        )

    print(line(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(line(row))


def run_dedupe(session, base_url: str, requests, *, execute: bool) -> int:
    assets = fetch_all_marketing_assets(session, base_url, requests)
    groups = find_duplicate_groups(assets)
    print_deletion_plan(groups)
    planned = sum(len(group.delete) for group in groups)
    print(
        f"\nPlan: grupos_duplicados={len(groups)}, elementos_por_borrar={planned}"
    )
    if not execute:
        print("Dry-run: no se borró ningún material. Usa --execute después de revisar la tabla.")
        return 0

    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        raise UploadError("La sesión no contiene la cookie csrftoken después del login.")
    headers = {"X-CSRFToken": csrf_token, "Referer": f"{base_url}/"}
    deleted = 0
    failures: list[tuple[int, str]] = []
    for group in groups:
        for duplicate in group.delete:
            duplicate_id = _numeric_id(duplicate)
            url = f"{base_url}{MARKETING_ASSETS_PATH}{duplicate_id}/"
            try:
                response = session.delete(url, headers=headers, timeout=30)
            except requests.RequestException as exc:
                failures.append((duplicate_id, str(exc)))
                print(f"FALLO id={duplicate_id}: {exc}")
                continue
            if response.status_code >= 400:
                reason = _response_reason(response)
                failures.append((duplicate_id, reason))
                print(f"FALLO id={duplicate_id}: {reason}")
                continue
            deleted += 1
            print(f"BORRADO id={duplicate_id}")

    print(
        "\nResumen final: "
        f"grupos_duplicados={len(groups)}, elementos_borrados={deleted}, "
        f"fallidos={len(failures)}"
    )
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detecta y elimina duplicados exactos de Materiales de Marketing."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="execute", action="store_false")
    mode.add_argument("--execute", dest="execute", action="store_true")
    parser.set_defaults(execute=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        requests, session, base_url = authenticated_api_session(args.base_url)
        return run_dedupe(session, base_url, requests, execute=args.execute)
    except UploadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
