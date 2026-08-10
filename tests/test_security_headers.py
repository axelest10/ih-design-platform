import re

import pytest
from django.conf import settings
from rest_framework.test import APIClient

EXPECTED_CSP_DIRECTIVES = {
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
}


@pytest.mark.parametrize("path", ["/", "/panel.html", "/login.html"])
def test_frontend_pages_include_strict_security_headers(path):
    response = APIClient().get(path)

    assert response.status_code == 200
    directives = {
        directive.strip()
        for directive in response["Content-Security-Policy"].split(";")
        if directive.strip()
    }
    assert directives == EXPECTED_CSP_DIRECTIVES
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "same-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response["X-Frame-Options"] == "DENY"


def test_navigable_frontend_is_compatible_with_strict_csp():
    frontend_root = settings.BASE_DIR / "frontend"
    for html_path in frontend_root.glob("*.html"):
        html = html_path.read_text(encoding="utf-8")
        assert "<style" not in html
        assert re.search(r"\sstyle\s*=", html) is None
        assert re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html) is None

    for script_path in (frontend_root / "scripts").glob("*.js"):
        script = script_path.read_text(encoding="utf-8")
        assert re.search(r"\.style(?:\.|\[|\s*=)", script) is None
