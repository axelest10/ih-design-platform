"""Eventos operativos estructurados con una superficie de datos deliberadamente pequeña."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar

LOGGER = logging.getLogger("ih_design.operations")
CORRELATION_ID: ContextVar[str] = ContextVar("correlation_id", default="")
ALLOWED_FIELDS = {
    "automated",
    "brief_id",
    "design_id",
    "duration_ms",
    "http_status",
    "output",
    "provider",
    "provider_message_id",
    "reason",
    "status",
    "template_key",
    "user_id",
    "version_id",
    "version_number",
}


def operation_event(event: str, **fields) -> None:
    """Registra solo campos operativos permitidos; cualquier otro dato se descarta."""
    payload = {
        "event": event,
        "correlation_id": CORRELATION_ID.get(),
        **{key: value for key, value in fields.items() if key in ALLOWED_FIELDS},
    }
    LOGGER.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str))
