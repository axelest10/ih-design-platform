"""Plan and optionally execute the controlled 50-design staging validation batch.

Dry-run is the default and performs no login or network request. Execution requires
``IH_DESIGN_USERNAME`` and ``IH_DESIGN_PASSWORD`` and never creates more designs than the
remaining slots reported by ``DESIGN_TEST_LIMIT`` (expected to remain 50).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

DEFAULT_BASE_URL = "https://ih-design-platform-production.up.railway.app"
DEFAULT_REPORT = Path("docs/testing/design-validation-batch-report.json")
BATCH_SIZE = 50
MAX_PROVIDER_CALLS_PER_DESIGN = 3  # prompt + structured copy + visual review

PRODUCTS = (
    "university-programmes",
    "business-english",
    "general-english",
    "ielts-preparation",
    "spanish-courses",
)
COUNTRIES = (
    ("MX", ("ih-mexico-drive-svg",)),
    ("CO", ("ih-bogota-svg", "ih-colombia-color", "ih-medellin-svg")),
    ("PE", ("ih-lima-svg",)),
    ("CL", ("ih-santiago-classic-svg",)),
)
FORMATS = ("square", "story", "portrait")
TONES = ("institucional", "cercano", "juvenil", "académico", "aspiracional")
OBJECTIVES = (
    "Dar a conocer el programa",
    "Generar registros de prueba",
    "Comunicar una sesión informativa",
    "Promover una experiencia educativa",
    "Solicitar información",
)
LANGUAGES = ("es", "en", "es")
CTAS = ("information", "register", "visit", "message", "event")
COPY_LENGTHS = ("short", "medium", "long")


class BatchError(RuntimeError):
    """Operational error safe to show without a traceback or secret values."""


@dataclass(frozen=True)
class ValidationCase:
    number: int
    title: str
    country: str
    product_slug: str
    format: str
    tone: str
    objective: str
    language: str
    cta: str
    copy_length: str
    brand_logo_key: str
    additional_logo_keys: tuple[str, ...]

    def brief_payload(self) -> dict:
        length_copy = {
            "short": "Una propuesta clara para avanzar.",
            "medium": "Una experiencia práctica con acompañamiento para avanzar con confianza.",
            "long": (
                "Una experiencia educativa práctica, flexible y cercana para desarrollar "
                "habilidades útiles en contextos académicos, personales y profesionales."
            ),
        }[self.copy_length]
        return {
            "title": self.title,
            "format": self.format,
            "country": self.country,
            "product_slug": self.product_slug,
            "brand_logo_key": self.brand_logo_key,
            "additional_logo_keys": list(self.additional_logo_keys),
            "audience": "Audiencia sintética del lote técnico de validación",
            "objective": self.objective,
            "requested_message": length_copy,
            "source_references": [],
            "visual_reference_urls": [],
            "language": self.language,
            "channel": "instagram",
            "brief_data": {
                "audience_need": "Evaluar claridad, jerarquía y adaptación del formato.",
                "campaign_info": "Prueba técnica; no publicar.",
                "required_information": "Contenido sintético sin datos personales.",
                "cta": self.cta,
                "cta_destination": "https://example.invalid/prueba",
                "tone": self.tone,
                "visual_elements": "Composición limpia dentro de la zona segura.",
            },
            "constraints": {
                "test_batch": "design-50-v1",
                "synthetic": True,
                "do_not_publish": True,
            },
        }


def build_cases() -> list[ValidationCase]:
    cases = []
    for index in range(BATCH_SIZE):
        country, logos = COUNTRIES[(index // len(PRODUCTS)) % len(COUNTRIES)]
        cases.append(
            ValidationCase(
                number=index + 1,
                title=f"[TEST-BATCH-50 {index + 1:02d}] Validación técnica",
                country=country,
                product_slug=PRODUCTS[index % len(PRODUCTS)],
                format=FORMATS[index % len(FORMATS)],
                tone=TONES[index % len(TONES)],
                objective=OBJECTIVES[index % len(OBJECTIVES)],
                language=LANGUAGES[index % len(LANGUAGES)],
                cta=CTAS[index % len(CTAS)],
                copy_length=COPY_LENGTHS[index % len(COPY_LENGTHS)],
                brand_logo_key=logos[index % len(logos)],
                additional_logo_keys=("hello-live-kids-svg",) if index % 2 == 0 else (),
            )
        )
    return cases


def _credentials() -> tuple[str, str]:
    username = os.getenv("IH_DESIGN_USERNAME", "").strip()
    password = os.getenv("IH_DESIGN_PASSWORD", "")
    if not username or not password:
        raise BatchError(
            "Faltan IH_DESIGN_USERNAME/IH_DESIGN_PASSWORD; no se ejecutó nada contra staging."
        )
    return username, password


def _requests_module():
    try:
        import requests
    except ImportError as exc:
        raise BatchError("Instala requests para usar --execute.") from exc
    return requests


def authenticated_session(base_url: str):
    username, password = _credentials()
    requests = _requests_module()
    session = requests.Session()
    base_url = base_url.rstrip("/")
    try:
        response = session.post(
            f"{base_url}/api/v1/auth/login/",
            json={"username": username, "password": password},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise BatchError(f"No se pudo conectar con staging: {exc}") from exc
    if response.status_code != 200:
        raise BatchError(f"El login falló con HTTP {response.status_code}.")
    if not session.cookies.get("csrftoken"):
        raise BatchError("El login no devolvió la cookie CSRF esperada.")
    return requests, session, base_url


def _response_payload(response) -> dict | list:
    try:
        return response.json()
    except ValueError as exc:
        raise BatchError(
            f"La API devolvió contenido no JSON (HTTP {response.status_code})."
        ) from exc


def fetch_collection(session, base_url: str, path: str, requests) -> list[dict]:
    items = []
    url = f"{base_url}{path}"
    while url:
        try:
            response = session.get(url, timeout=30)
        except requests.RequestException as exc:
            raise BatchError(f"No se pudo consultar {path}: {exc}") from exc
        if response.status_code >= 400:
            raise BatchError(f"No se pudo consultar {path}: HTTP {response.status_code}.")
        payload = _response_payload(response)
        if isinstance(payload, list):
            items.extend(payload)
            break
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise BatchError(f"Formato inesperado al consultar {path}.")
        items.extend(payload["results"])
        url = urljoin(f"{base_url}/", payload.get("next")) if payload.get("next") else ""
    return items


def _write_headers(session, base_url: str) -> dict[str, str]:
    token = session.cookies.get("csrftoken")
    if not token:
        raise BatchError("La sesión perdió la cookie CSRF.")
    return {"X-CSRFToken": token, "Referer": f"{base_url}/"}


def post_json(session, base_url: str, path: str, payload: dict, requests) -> dict:
    try:
        response = session.post(
            f"{base_url}{path}",
            json=payload,
            headers=_write_headers(session, base_url),
            timeout=180,
        )
    except requests.RequestException as exc:
        raise BatchError(f"Falló POST {path}: {exc}") from exc
    body = _response_payload(response)
    if response.status_code >= 400:
        detail = body.get("detail") if isinstance(body, dict) else None
        raise BatchError(f"POST {path} devolvió HTTP {response.status_code}: {detail or body}")
    if not isinstance(body, dict):
        raise BatchError(f"POST {path} devolvió una estructura inesperada.")
    return body


def _existing_design_by_brief(designs: list[dict]) -> dict[str, dict]:
    return {str(design.get("brief")): design for design in designs if design.get("brief")}


def _result(case: ValidationCase, *, state: str, detail: str = "", design=None) -> dict:
    design = design or {}
    versions = design.get("versions") or []
    latest = versions[0] if versions else {}
    validation = latest.get("validation_summary") or {}
    return {
        "number": case.number,
        "country": case.country,
        "product": case.product_slug,
        "format": case.format,
        "state": state,
        "detail": detail,
        "design_id": design.get("id"),
        "design_status": design.get("status", "not_created"),
        "test_number": design.get("test_number"),
        "latest_version": latest.get("number"),
        "version_count": len(versions),
        "renderer_result": validation.get("status", "not_run"),
        "automatic_review_status": latest.get("claude_review_status", "not_run"),
        "automatic_review": latest.get("claude_review") or {},
    }


def execute_batch(cases: list[ValidationCase], base_url: str, report_path: Path) -> int:
    requests, session, base_url = authenticated_session(base_url)
    profile_response = session.get(f"{base_url}/api/v1/me/", timeout=30)
    profile = _response_payload(profile_response)
    if profile_response.status_code != 200 or not isinstance(profile, dict):
        raise BatchError("No se pudo verificar el perfil de staging.")
    if not profile.get("design_test_mode"):
        raise BatchError("DESIGN_TEST_MODE no está activo; el lote fue cancelado.")
    limit = int(profile.get("design_test_limit") or 0)
    if limit != BATCH_SIZE:
        raise BatchError(f"DESIGN_TEST_LIMIT debe seguir en {BATCH_SIZE}; staging reportó {limit}.")
    if not profile.get("can_create_briefs"):
        raise BatchError("La cuenta configurada no puede crear diseños.")

    briefs = fetch_collection(session, base_url, "/api/v1/briefs/", requests)
    designs = fetch_collection(session, base_url, "/api/v1/designs/", requests)
    brief_by_title = {str(item.get("title")): item for item in briefs}
    design_by_brief = _existing_design_by_brief(designs)
    used_test_numbers = {
        int(item["test_number"])
        for item in designs
        if item.get("test_number") is not None and 1 <= int(item["test_number"]) <= limit
    }
    remaining_slots = max(0, limit - len(used_test_numbers))
    results = []
    created = 0

    for case in cases:
        brief = brief_by_title.get(case.title)
        existing_design = design_by_brief.get(str(brief.get("id"))) if brief else None
        if existing_design:
            results.append(_result(case, state="already_exists", design=existing_design))
            continue
        if created >= remaining_slots:
            results.append(_result(case, state="blocked_by_test_limit"))
            continue
        try:
            if brief is None:
                brief = post_json(
                    session,
                    base_url,
                    "/api/v1/briefs/",
                    case.brief_payload(),
                    requests,
                )
            prompted = post_json(
                session,
                base_url,
                f"/api/v1/briefs/{brief['id']}/generate-prompt/",
                {},
                requests,
            )
            generated_prompt = str(prompted.get("generated_prompt") or "").strip()
            if not generated_prompt:
                raise BatchError("El proveedor de copy no devolvió contenido; no se confirmó.")
            design = post_json(
                session,
                base_url,
                f"/api/v1/briefs/{brief['id']}/confirm-design/",
                {"prompt_override": generated_prompt},
                requests,
            )
        except BatchError as exc:
            results.append(_result(case, state="failed", detail=str(exc)))
            continue
        created += 1
        results.append(_result(case, state="created", design=design))

    report = {
        "schema": "ih-design-validation-batch/v1",
        "synthetic": True,
        "base_url": base_url,
        "design_test_limit": limit,
        "remaining_slots_at_start": remaining_slots,
        "maximum_provider_calls": remaining_slots * MAX_PROVIDER_CALLS_PER_DESIGN,
        "summary": {
            "planned": len(cases),
            "created": sum(item["state"] == "created" for item in results),
            "already_exists": sum(item["state"] == "already_exists" for item in results),
            "failed": sum(item["state"] == "failed" for item in results),
            "blocked_by_test_limit": sum(
                item["state"] == "blocked_by_test_limit" for item in results
            ),
        },
        "results": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False))
    print(f"Reporte: {report_path}")
    return 1 if report["summary"]["failed"] else 0


def print_plan(cases: list[ValidationCase]) -> None:
    print("# | País | Producto | Formato | Idioma | Largo | Logo adicional")
    for case in cases:
        print(
            f"{case.number:02d} | {case.country} | {case.product_slug} | {case.format} | "
            f"{case.language} | {case.copy_length} | "
            f"{'sí' if case.additional_logo_keys else 'no'}"
        )
    print(
        f"\nPlan: {len(cases)} diseños sintéticos; máximo teórico de llamadas de proveedor: "
        f"{len(cases) * MAX_PROVIDER_CALLS_PER_DESIGN}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida el lote controlado de 50 diseños.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cases = build_cases()
    if not args.execute:
        print_plan(cases)
        print("Dry-run: no se hizo login, no hubo red y no se creó ningún registro.")
        return 0
    try:
        return execute_batch(cases, args.base_url, args.report)
    except BatchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
