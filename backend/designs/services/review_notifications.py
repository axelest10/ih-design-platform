"""Punto de extensión para notificaciones de revisión; no envía mensajes todavía."""
from __future__ import annotations


def notify_review_transition(*, design, version, decision, comment=None) -> None:
    """Reserva el hook de notificaciones para una integración futura."""
    return None
