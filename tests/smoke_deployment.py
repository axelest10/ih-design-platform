"""Smoke test explícito del healthcheck desplegado; no pertenece a la suite normal."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

EXPECTED_HEALTH = {"status": "ok", "service": "ih-design-platform"}
HEALTH_PATH = "/api/v1/health/"
TIMEOUT_SECONDS = 20


def _health_url() -> str:
    base_url = os.getenv("SMOKE_TEST_BASE_URL", "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "SMOKE_TEST_BASE_URL debe ser una URL http(s) completa, sin incluir el health path."
        )
    return f"{base_url}{HEALTH_PATH}"


def main() -> int:
    try:
        health_url = _health_url()
    except ValueError as exc:
        print(f"ERROR configuración: {exc}", file=sys.stderr)
        return 2

    request = Request(
        health_url,
        headers={"Accept": "application/json", "User-Agent": "ih-design-platform-smoke/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            status = response.status
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        print(f"ERROR HTTP {exc.code} {health_url}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"ERROR red {health_url}: {exc.reason}", file=sys.stderr)
        return 1

    if status != 200:
        print(f"ERROR status esperado=200 recibido={status} {health_url}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        print(f"ERROR JSON inválido {health_url}: {exc}", file=sys.stderr)
        return 1

    if payload != EXPECTED_HEALTH:
        print(
            f"ERROR JSON esperado={EXPECTED_HEALTH!r} recibido={payload!r}",
            file=sys.stderr,
        )
        return 1

    print(f"OK {status} {health_url} {payload!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
