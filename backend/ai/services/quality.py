"""Validación ligera y reutilizable de respuestas IA antes de su uso humano."""
from __future__ import annotations

import json
import re
from typing import Any


def validate_ai_output(
    content: str, authorized_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Señaliza cifras, URLs y afirmaciones potencialmente no verificables."""
    context_text = json.dumps(authorized_context or {}, ensure_ascii=False)
    text = str(content or "")
    flags: list[dict[str, str]] = []
    generated_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text))
    authorized_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", context_text))
    for value in sorted(generated_numbers - authorized_numbers):
        flags.append({"type": "unverified_number", "value": value})
    generated_urls = set(re.findall(r"https?://[^\s\"']+", text))
    authorized_urls = set(re.findall(r"https?://[^\s\"']+", context_text))
    for value in sorted(generated_urls - authorized_urls):
        flags.append({"type": "unverified_url", "value": value})
    risky_phrases = ("garantizado", "número 1", "sin esfuerzo", "resultados asegurados")
    for phrase in risky_phrases:
        if (
            phrase.casefold() in text.casefold()
            and phrase.casefold() not in context_text.casefold()
        ):
            flags.append({"type": "unverified_claim", "value": phrase})
    return {"status": "needs_review" if flags else "passed", "flags": flags}
