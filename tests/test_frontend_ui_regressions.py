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
        assert "asset_url 'styles/logo-combobox.css'" in html
        assert html.index("asset_url 'scripts/logo-combobox.js'") < html.index(
            f"asset_url 'scripts/{script_name}'"
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
    prompt_section = html.split('id="prompt-review-step"', 1)[1].split(
        'id="design-final-step"', 1
    )[0]
    assert prompt_section.count('class="loading-indicator__dot"') == 5
    assert 'id="brief-submit"' in html
    assert "asset_url 'styles/loading-indicator.css'" in html
    assert "loading.hidden = false" in script
    assert "submitButton.disabled = true" in script
    assert "} finally {" in script
    assert "loading.hidden = true" in script
    assert "submitButton.disabled = false" in script
    assert "@keyframes ih-system-processing" in css
    assert "linear-gradient" not in css
    for color in ("#3b44b5", "#f06c6a", "#e070a2", "#f4ab63", "#f4cf80", "#b7db6e"):
        assert color in css


def test_brief_form_is_disabled_for_authenticated_read_only_roles():
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")

    assert "setBriefFormDisabled(!user.can_create_briefs)" in script
    assert "setBriefFormDisabled(false)" not in script


def test_prompt_review_step_is_present_and_hidden_by_default():
    html = (FRONTEND / "panel.html").read_text(encoding="utf-8")
    section = html.split('id="prompt-review-step"', 1)[1].split(">", 1)[0]

    assert "hidden" in section
    assert 'id="generated-prompt"' in html
    assert 'rows="8"' in html
    assert 'id="prompt-manual-notice"' in html
    assert 'id="prompt-continue"' in html
    assert 'id="prompt-back"' in html
    assert "maxlength" not in html.split('id="generated-prompt"', 1)[1].split(">", 1)[0]


def test_brief_creation_requests_prompt_after_brief_and_reference_are_saved():
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")

    brief_created = script.index("const brief = await json(response)")
    reference_saved = script.index('"/api/v1/brief-reference-uploads/"')
    prompt_requested = script.index("/generate-prompt/")
    prompt_shown = script.index("showPromptReview(promptedBrief)")

    assert brief_created < reference_saved < prompt_requested < prompt_shown


def test_prompt_continue_patches_only_when_text_changed():
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    handler = script.split("const continueFromPrompt", 1)[1].split(
        "const createBrief", 1
    )[0]

    assert "if (prompt !== state.originalPrompt)" in handler
    assert 'method: "PATCH"' in handler
    assert handler.index("if (prompt !== state.originalPrompt)") < handler.index(
        'method: "PATCH"'
    )
    assert 'prompt_source: "ai_edited"' in handler


def test_prompt_back_only_changes_the_visible_step_without_network_calls():
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    handler = script.split("const returnToBrief", 1)[1].split(
        "const continueFromPrompt", 1
    )[0]

    assert '$("prompt-review-step").hidden = true' in handler
    assert '$("brief-form").hidden = false' in handler
    assert "fetch(" not in handler
    assert "authenticatedFetch" not in handler


def test_design_final_step_uses_the_persisted_svg_preview_and_starts_hidden():
    html = (FRONTEND / "panel.html").read_text(encoding="utf-8")
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    section = html.split('id="design-final-step"', 1)[1].split(">", 1)[0]

    assert "hidden" in section
    assert 'id="design-preview"' in html
    assert 'id="design-save"' in html
    assert "asset_url 'styles/design-final.css'" in html
    assert "const svg = version?.render_data?.svg" in script
    assert "data:image/svg+xml;charset=utf-8" in script
    assert '$("design-final-step").hidden = false' in script


def test_prompt_continue_calls_confirm_design_after_optional_patch():
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    handler = script.split("const continueFromPrompt", 1)[1].split(
        "const saveDesign", 1
    )[0]

    assert handler.index('method: "PATCH"') < handler.index("/confirm-design/")
    assert 'method: "POST"' in handler
    assert "showDesignFinal(design)" in handler


def test_design_generation_reuses_loading_indicator_in_prompt_step():
    html = (FRONTEND / "panel.html").read_text(encoding="utf-8")
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    prompt_section = html.split('id="prompt-review-step"', 1)[1].split(
        'id="design-final-step"', 1
    )[0]

    assert html.count('id="brief-loading"') == 1
    assert 'id="brief-loading"' in prompt_section
    assert "loading.hidden = false" in script
    assert "loading.hidden = true" in script


def test_design_save_only_confirms_completion_without_network_call():
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    handler = script.split("const saveDesign", 1)[1].split(
        "const createBrief", 1
    )[0]

    assert "listo para continuar con el flujo de revisión" in handler
    assert 'link.href = "review.html"' in handler
    assert "fetch(" not in handler
    assert "authenticatedFetch" not in handler


def test_design_final_step_requests_independent_revisions_and_updates_preview():
    html = (FRONTEND / "panel.html").read_text(encoding="utf-8")
    script = (FRONTEND / "scripts" / "panel.js").read_text(encoding="utf-8")
    handler = script.split("const requestDesignRevision", 1)[1].split(
        "const returnToBrief", 1
    )[0]

    assert 'id="design-revision-form"' in html
    assert 'id="design-revision-instruction"' in html
    assert 'id="design-revision-history"' in html
    assert 'id="design-revision-loading"' in html
    revision_section = html.split('id="design-revision-loading"', 1)[1].split(
        "</div>", 2
    )[0]
    assert revision_section.count('class="loading-indicator__dot"') == 5
    assert "/revise/" in handler
    assert "body: JSON.stringify({ instruction })" in handler
    assert "renderDesignPreview(design)" in handler
    assert "revisionInstructions.push(instruction)" in handler
    assert "instruction_history" not in handler
    assert "maxAttempts" not in handler
