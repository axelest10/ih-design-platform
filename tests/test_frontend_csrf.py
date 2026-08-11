from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
SCRIPT_PAGES = (
    ("admin.html", "admin.js"),
    ("login.html", "login.js"),
    ("panel.html", "panel.js"),
    ("review.html", "review.js"),
    ("school-kit.html", "school-kit.js"),
    ("templates-gallery.html", "templates-gallery.js"),
)


@pytest.mark.parametrize(("page_name", "script_name"), SCRIPT_PAGES)
def test_mutating_pages_load_shared_csrf_helper_before_page_script(
    page_name, script_name
):
    html = (FRONTEND / page_name).read_text(encoding="utf-8")

    assert html.index('src="scripts/csrf.js"') < html.index(
        f'src="scripts/{script_name}"'
    )


def test_shared_authenticated_fetch_adds_csrf_only_to_non_get_requests():
    script = (FRONTEND / "scripts" / "csrf.js").read_text(encoding="utf-8")

    assert 'const method = String(options.method || "GET").toUpperCase()' in script
    assert 'if (method !== "GET")' in script
    assert 'cookie("csrftoken")' in script
    assert 'headers.set("X-CSRFToken"' in script
    assert "return fetch(url, { ...options, headers })" in script


def test_authenticated_mutations_use_shared_fetch_helper():
    scripts = {
        name: (FRONTEND / "scripts" / name).read_text(encoding="utf-8")
        for _, name in SCRIPT_PAGES
    }

    assert 'window.authenticatedFetch(url, options)' in scripts["admin.js"]
    assert 'window.authenticatedFetch(url, options)' in scripts["review.js"]
    assert 'window.authenticatedFetch("/api/v1/auth/login/"' in scripts["login.js"]
    assert scripts["panel.js"].count("window.authenticatedFetch") == 7
    assert 'window.authenticatedFetch("/api/v1/materials/quick-design/"' in scripts[
        "templates-gallery.js"
    ]
    assert scripts["school-kit.js"].count("window.authenticatedFetch") == 3

    for script in scripts.values():
        assert "X-CSRFToken" not in script
        assert "const cookie" not in script
