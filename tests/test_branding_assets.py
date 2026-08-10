"""Pruebas de activos de marca: manifests de iconos/rainbows/globos/logos y validación de logos."""
from __future__ import annotations

import pytest

from branding.services import loader, validators


@pytest.fixture(autouse=True)
def _clear_brand_cache():
    loader.clear_cache()
    yield
    loader.clear_cache()


def test_icon_manifest_has_six_documented_icons():
    manifest = loader.load_icon_manifest()
    names = {icon["name"] for icon in manifest["icons"]}
    assert names == {"Knowledge", "Excellence", "Communication", "Innovation", "Growth", "Study"}


def test_icon_manifest_files_exist_on_disk():
    manifest = loader.load_icon_manifest()
    base_dir = loader.ASSETS_DIR / "icons"
    missing = validators.missing_asset_files(manifest, base_dir)
    assert missing == [], f"Archivos de ícono faltantes: {missing}"


def test_rainbow_manifest_files_exist_on_disk():
    manifest = loader.load_rainbow_manifest()
    base_dir = loader.ASSETS_DIR / "rainbows"
    missing = validators.missing_asset_files(manifest, base_dir)
    assert missing == [], f"Archivos de rainbow faltantes: {missing}"


def test_globe_manifest_files_exist_on_disk():
    manifest = loader.load_globe_manifest()
    base_dir = loader.ASSETS_DIR / "illustrations" / "globes"
    missing = validators.missing_asset_files(manifest, base_dir)
    assert missing == [], f"Archivos de globo faltantes: {missing}"


def test_logo_manifest_exists_and_is_partially_loaded():
    manifest = loader.load_logo_manifest()
    assert manifest["status"] == "partial"
    variants_loaded = {entry["variant"] for entry in manifest["logos"]}
    assert {
        "classic",
        "black",
        "white",
        "monochrome-blue",
        "monochrome-white",
    }.issubset(variants_loaded)
    # Aún pendientes de carga, por instrucción explícita del proyecto.
    assert "white-reversed" not in variants_loaded
    assert "dual-branding" not in variants_loaded


def test_all_loaded_logos_are_approved():
    manifest = loader.load_logo_manifest()
    for entry in manifest["logos"]:
        assert entry["approved"] is True, f"Logo '{entry['name']}' cargado pero no aprobado."


def test_loaded_logo_files_exist_on_disk():
    manifest = loader.load_logo_manifest()
    base_dir = loader.ASSETS_DIR / "logos"
    missing = validators.missing_asset_files(manifest, base_dir)
    assert missing == [], f"Archivos de logo faltantes: {missing}"


def test_loaded_logos_pass_validate_logo():
    manifest = loader.load_logo_manifest()
    for entry in manifest["logos"]:
        result = validators.validate_logo(entry["name"])
        msg = f"Logo '{entry['name']}' registrado como aprobado pero rechazado: {result.reason}"
        assert result.is_valid, msg


def test_logo_manifest_documents_expected_variants():
    manifest = loader.load_logo_manifest()
    variants = {v["variant"] for v in manifest["expected_variants"]}
    assert variants == {"classic", "black", "white", "white-reversed", "dual-branding"}


def test_unregistered_logo_is_rejected():
    result = validators.validate_logo("logo-que-no-existe")
    assert not result.is_valid
    assert "no está registrado" in result.reason


def test_logo_registered_but_not_approved_is_rejected(monkeypatch):
    fake_manifest = {
        "logos": [
            {"name": "borrador-no-aprobado", "approved": False},
        ]
    }
    monkeypatch.setattr(loader, "load_logo_manifest", lambda: fake_manifest)
    result = validators.validate_logo("borrador-no-aprobado")
    assert not result.is_valid
    assert "no aprobado" in result.reason


def test_logo_registered_and_approved_is_accepted(monkeypatch):
    fake_manifest = {
        "logos": [
            {"name": "ih-mexico-classic", "approved": True},
        ]
    }
    monkeypatch.setattr(loader, "load_logo_manifest", lambda: fake_manifest)
    result = validators.validate_logo("ih-mexico-classic")
    assert result.is_valid


def test_logos_directory_structure_is_prepared_for_upload():
    logos_dir = loader.ASSETS_DIR / "logos"
    for expected_subdir in ("classic", "black", "white", "white-reversed", "dual-branding"):
        msg = f"Falta la carpeta {expected_subdir}/ en brand/assets/logos/"
        assert (logos_dir / expected_subdir).is_dir(), msg


def test_open_sans_font_files_and_license_are_present():
    fonts_dir = loader.ASSETS_DIR / "fonts" / "open-sans"
    assert (fonts_dir / "OFL.txt").exists()
    ttf_files = list(fonts_dir.glob("*.ttf"))
    assert ttf_files, "No se encontraron archivos .ttf de Open Sans."


def test_aptos_font_files_are_not_redistributed_without_confirmed_license():
    """Por diseño: no debemos redistribuir Aptos hasta confirmar la licencia con el cliente."""
    aptos_dir = loader.ASSETS_DIR / "fonts" / "aptos"
    if aptos_dir.exists():
        ttf_files = list(aptos_dir.glob("*.ttf"))
        assert ttf_files == [], (
            "Se encontraron archivos .ttf de Aptos sin que exista confirmación de licencia "
            "registrada en brand/tokens/typography.yaml (license_status debe dejar de ser UNKNOWN)."
        )
