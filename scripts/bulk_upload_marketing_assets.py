"""Inventory and upload MarketingAsset files through the production API.

Dry-run is the default and performs no network requests. Real uploads require
``--execute`` plus ``IH_DESIGN_USERNAME`` and ``IH_DESIGN_PASSWORD``.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "https://ih-design-platform-production.up.railway.app"
MAX_BATCH_FILES = 30
MAX_FILE_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf", "ppt", "pptx", "docx"}

# Ajusta o amplía este diccionario después de revisar el dry-run si Drive usa otros nombres.
CATEGORY_RULES = {
    "foto de perfil": "foto_perfil",
    "fotos de perfil": "foto_perfil",
    "zoom": "zoom_background",
    "background computadora": "background_computadora",
    "fondo computadora": "background_computadora",
    "desktop": "background_computadora",
    "background celular": "background_celular",
    "fondo celular": "background_celular",
    "mobile": "background_celular",
    "firma": "firma_electronica",
    "banner linkedin": "banner_linkedin",
    "linkedin": "banner_linkedin",
    "template ppt": "template_ppt",
    "plantilla ppt": "template_ppt",
    "powerpoint": "template_ppt",
}

COUNTRY_CODES = {
    "mexico": "MX",
    "mx": "MX",
    "colombia": "CO",
    "co": "CO",
    "chile": "CL",
    "cl": "CL",
    "peru": "PE",
    "pe": "PE",
}


@dataclass(frozen=True)
class AssetCandidate:
    path: Path
    relative_path: str
    brand: str
    country: str
    category: str
    label: str
    reason: str = ""

    @property
    def valid(self) -> bool:
        return not self.reason


class UploadError(RuntimeError):
    """Expected operational error that is safe to show without a traceback."""


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    separated = without_accents.casefold().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", separated).strip()


def label_from_filename(filename: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", Path(filename).stem)).strip()


def _brand_and_directories(source: Path, path: Path) -> tuple[str, list[str], str]:
    relative = path.relative_to(source)
    directories = [source.name, *relative.parts[:-1]]
    for index, directory in enumerate(directories):
        normalized = normalize_text(directory)
        if normalized.startswith("international house"):
            return "ih", directories[index + 1 :], ""
        if normalized.startswith("ielts"):
            return "ielts", directories[index + 1 :], ""
    return "", [], "sin marca reconocida"


def _country_from_directories(brand: str, directories: list[str]) -> str:
    if not directories:
        return ""
    first = directories[0]
    known = COUNTRY_CODES.get(normalize_text(first))
    if known:
        return known
    return first.upper() if brand == "ih" else ""


def _category_from_directories(directories: list[str]) -> str:
    searchable = normalize_text(" ".join(directories))
    for substring, category in CATEGORY_RULES.items():
        if normalize_text(substring) in searchable:
            return category
    return ""


def inspect_file(source: Path, path: Path) -> AssetCandidate:
    relative_path = str(path.relative_to(source))
    brand, directories, brand_error = _brand_and_directories(source, path)
    country = _country_from_directories(brand, directories)
    category = _category_from_directories(directories)
    label = label_from_filename(path.name)

    reason = brand_error
    extension = path.suffix.casefold().lstrip(".")
    if not reason and extension not in ALLOWED_EXTENSIONS:
        reason = f"extensión no permitida: .{extension or '(sin extensión)'}"
    if not reason:
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                reason = "archivo mayor a 25 MB"
        except OSError as exc:
            reason = f"no se pudo leer el archivo: {exc}"
    if not reason and not category:
        reason = "sin categoría reconocida"

    return AssetCandidate(
        path=path,
        relative_path=relative_path,
        brand=brand,
        country=country,
        category=category,
        label=label,
        reason=reason,
    )


def scan_assets(source: Path) -> list[AssetCandidate]:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise UploadError(f"La carpeta de origen no existe o no es un directorio: {source}")
    files = sorted(
        (path for path in source.rglob("*") if path.is_file()),
        key=lambda path: normalize_text(str(path.relative_to(source))),
    )
    return [inspect_file(source, path) for path in files]


def _shorten(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"


def print_inventory(candidates: list[AssetCandidate]) -> None:
    headers = ("Archivo", "Brand", "País", "Categoría", "Label", "Estado")
    rows = [
        (
            candidate.relative_path,
            candidate.brand or "—",
            candidate.country or "Global",
            candidate.category or "—",
            candidate.label or "—",
            candidate.reason or "listo",
        )
        for candidate in candidates
    ]
    limits = (58, 7, 12, 24, 34, 42)
    widths = [
        min(limits[index], max(len(headers[index]), *(len(row[index]) for row in rows)))
        if rows
        else len(headers[index])
        for index in range(len(headers))
    ]

    def line(values: tuple[str, ...]) -> str:
        return " | ".join(
            _shorten(value, widths[index]).ljust(widths[index])
            for index, value in enumerate(values)
        )

    print(line(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(line(row))


def _chunks(items: list[AssetCandidate], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _credentials() -> tuple[str, str]:
    username = os.getenv("IH_DESIGN_USERNAME", "").strip()
    password = os.getenv("IH_DESIGN_PASSWORD", "")
    missing = [
        name
        for name, value in (
            ("IH_DESIGN_USERNAME", username),
            ("IH_DESIGN_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise UploadError(
            "Faltan variables de entorno para ejecutar la carga: "
            f"{', '.join(missing)}. Expórtalas antes de usar --execute."
        )
    return username, password


def _requests_module():
    try:
        import requests
    except ImportError as exc:
        raise UploadError(
            "No está instalado 'requests'. Instálalo con: python -m pip install requests"
        ) from exc
    return requests


def _response_reason(response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return str(payload.get("detail") or f"HTTP {response.status_code}")


def _upload_batch(session, base_url: str, batch: list[AssetCandidate]):
    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        raise UploadError("La sesión no contiene la cookie csrftoken después del login.")

    handles = []
    multipart = []
    try:
        for candidate in batch:
            handle = candidate.path.open("rb")
            handles.append(handle)
            content_type = (
                mimetypes.guess_type(candidate.path.name)[0] or "application/octet-stream"
            )
            multipart.append(("files", (candidate.path.name, handle, content_type)))
        first = batch[0]
        return session.post(
            f"{base_url}/api/v1/materials/marketing-assets/bulk/",
            data={
                "brand": first.brand,
                "country": first.country,
                "category": first.category,
            },
            files=multipart,
            headers={"X-CSRFToken": csrf_token},
            timeout=180,
        )
    finally:
        for handle in handles:
            handle.close()


def execute_upload(candidates: list[AssetCandidate], base_url: str) -> int:
    username, password = _credentials()
    requests = _requests_module()
    session = requests.Session()
    base_url = base_url.rstrip("/")
    try:
        login_response = session.post(
            f"{base_url}/api/v1/auth/login/",
            json={"username": username, "password": password},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise UploadError(f"No se pudo conectar con la plataforma: {exc}") from exc
    if login_response.status_code != 200:
        raise UploadError(f"El login falló con HTTP {login_response.status_code}.")
    if not session.cookies.get("csrftoken"):
        raise UploadError("El login fue exitoso, pero no devolvió la cookie csrftoken.")

    valid = [candidate for candidate in candidates if candidate.valid]
    groups: dict[tuple[str, str, str], list[AssetCandidate]] = defaultdict(list)
    for candidate in valid:
        groups[(candidate.brand, candidate.country, candidate.category)].append(candidate)

    uploaded = 0
    server_failures: list[tuple[str, str]] = []
    for group_key in sorted(groups):
        for batch in _chunks(groups[group_key], MAX_BATCH_FILES):
            brand, country, category = group_key
            print(
                f"Subiendo lote: brand={brand}, country={country or 'Global'}, "
                f"category={category}, archivos={len(batch)}"
            )
            try:
                response = _upload_batch(session, base_url, batch)
            except (OSError, requests.RequestException) as exc:
                server_failures.extend((item.relative_path, str(exc)) for item in batch)
                continue
            if response.status_code >= 400:
                reason = _response_reason(response)
                server_failures.extend((item.relative_path, reason) for item in batch)
                continue
            try:
                payload = response.json()
            except ValueError:
                server_failures.extend(
                    (item.relative_path, "respuesta del servidor sin JSON válido") for item in batch
                )
                continue
            uploaded += int(payload.get("created_count", 0))
            server_failures.extend(
                (
                    failure.get("filename", "archivo desconocido"),
                    failure.get("reason", "sin motivo"),
                )
                for failure in payload.get("failed", [])
            )

    skipped = [candidate for candidate in candidates if not candidate.valid]
    if skipped:
        print("\nOmitidos localmente:")
        for candidate in skipped:
            print(f"- {candidate.relative_path}: {candidate.reason}")
    if server_failures:
        print("\nFallidos en servidor:")
        for filename, reason in server_failures:
            print(f"- {filename}: {reason}")
    print(
        "\nResumen final: "
        f"encontrados={len(candidates)}, subidos={uploaded}, "
        f"omitidos={len(skipped)}, fallidos={len(server_failures)}"
    )
    return 1 if server_failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventaría y carga Materiales de Marketing por lotes."
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="Carpeta con los zips extraídos."
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
        candidates = scan_assets(args.source)
        print_inventory(candidates)
        valid_count = sum(candidate.valid for candidate in candidates)
        print(
            f"\nResumen dry-run: encontrados={len(candidates)}, "
            f"listos={valid_count}, omitidos={len(candidates) - valid_count}"
        )
        if not args.execute:
            print(
                "Dry-run: no se hizo login ni se subió ningún archivo. "
                "Usa --execute para cargar."
            )
            return 0
        return execute_upload(candidates, args.base_url)
    except UploadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
