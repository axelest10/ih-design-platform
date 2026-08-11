from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def test_marketing_asset_extension_uses_clean_file_url():
    script = (FRONTEND / "scripts" / "marketing-materials.js").read_text(
        encoding="utf-8"
    )

    assert 'String(asset.file_url || "").split(/[?#]/, 1)[0]' in script
    assert 'const dotIndex = filename.lastIndexOf(".")' in script
    assert 'return dotIndex === -1 ? ""' in script
    assert 'String(asset.file || "")' not in script


def test_logo_combobox_preserves_submission_controls_and_distinguishes_variants():
    component = (FRONTEND / "scripts" / "logo-combobox.js").read_text(
        encoding="utf-8"
    )
    panel = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    school_kit = (FRONTEND / "scripts" / "school-kit.js").read_text(
        encoding="utf-8"
    )
    gallery = (FRONTEND / "scripts" / "templates-gallery.js").read_text(
        encoding="utf-8"
    )

    assert "normalize(logo.brand).includes(query)" in component
    assert "normalize(logo.name).includes(query)" in component
    assert 'input.type = "checkbox"' in component
    assert "input.checked = true" in component
    assert "brand.textContent = logo.brand || logo.name" in component
    assert "name.textContent = logo.name" in component
    assert 'event.key === "Enter"' in component
    assert "selected.delete(name)" in component
    assert 'document.querySelectorAll("#additional-logos input:checked")' in panel
    assert 'selectedValues("#additional-logos")' in school_kit
    assert 'document.querySelector("#quick-additional-logos").selectedOptions' in gallery


def test_logo_combobox_assets_load_before_page_scripts():
    for page_name, script_name in (
        ("panel.html", "panel.js"),
        ("school-kit.html", "school-kit.js"),
        ("templates-gallery.html", "templates-gallery.js"),
    ):
        html = (FRONTEND / page_name).read_text(encoding="utf-8")
        assert 'href="styles/logo-combobox.css"' in html
        assert html.index('src="scripts/logo-combobox.js"') < html.index(
            f'src="scripts/{script_name}"'
        )


def test_admin_actions_have_a_non_overlapping_stack_layout():
    html = (FRONTEND / "panel.html").read_text(encoding="utf-8")
    css = (FRONTEND / "styles" / "panel-sidebar.css").read_text(encoding="utf-8")

    assert '<div class="admin-actions">' in html
    assert "display: grid" in css
    assert "gap: 10px" in css
    assert "min-height: 44px" in css


def test_brief_form_has_a_bounded_loading_state():
    html = (FRONTEND / "panel.html").read_text(encoding="utf-8")
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    css = (FRONTEND / "styles" / "loading-indicator.css").read_text(
        encoding="utf-8"
    )

    assert 'id="brief-loading"' in html
    assert 'class="loading-indicator"' in html
    assert "hidden" in html
    assert html.count('class="loading-indicator__dot"') == 5
    assert 'id="brief-submit"' in html
    assert 'href="styles/loading-indicator.css"' in html
    assert "loading.hidden = false" in script
    assert "submitButton.disabled = true" in script
    assert "} finally {" in script
    assert "loading.hidden = true" in script
    assert "submitButton.disabled = false" in script
    assert "@keyframes ih-system-processing" in css
    assert "linear-gradient" not in css
    for color in ("#3b44b5", "#f06c6a", "#e070a2", "#f4ab63", "#f4cf80", "#b7db6e"):
        assert color in css
