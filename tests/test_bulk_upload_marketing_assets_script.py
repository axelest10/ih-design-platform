import pytest
from scripts.bulk_upload_marketing_assets import UploadError, execute_upload, main, scan_assets


def test_scan_assets_infers_brand_country_category_and_label(tmp_path):
    source = tmp_path / "inventario"
    files = (
        source / "INTERNATIONAL HOUSE" / "México" / "Fotos de perfil" / "IH-MX_perfil.png",
        source / "INTERNATIONAL HOUSE" / "Colombia" / "Desktop" / "COL 1-100.jpg",
        source / "IELTS" / "Firmas electrónicas" / "IELTS_FIRMA.docx",
        source / "IELTS" / "Carpeta desconocida" / "sin-categoria.pdf",
    )
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test")

    candidates = scan_assets(source)
    by_name = {candidate.path.name: candidate for candidate in candidates}

    mexico = by_name["IH-MX_perfil.png"]
    assert (mexico.brand, mexico.country, mexico.category, mexico.label) == (
        "ih",
        "MX",
        "foto_perfil",
        "IH MX perfil",
    )
    colombia = by_name["COL 1-100.jpg"]
    assert (colombia.brand, colombia.country, colombia.category, colombia.label) == (
        "ih",
        "CO",
        "background_computadora",
        "COL 1 100",
    )
    ielts = by_name["IELTS_FIRMA.docx"]
    assert (ielts.brand, ielts.country, ielts.category) == (
        "ielts",
        "",
        "firma_electronica",
    )
    assert by_name["sin-categoria.pdf"].reason == "sin categoría reconocida"


def test_dry_run_is_default_and_does_not_require_credentials(tmp_path, monkeypatch, capsys):
    source = tmp_path / "INTERNATIONAL HOUSE" / "PE" / "Zoom"
    source.mkdir(parents=True)
    (source / "fondo_zoom.png").write_bytes(b"test")
    monkeypatch.delenv("IH_DESIGN_USERNAME", raising=False)
    monkeypatch.delenv("IH_DESIGN_PASSWORD", raising=False)

    result = main(["--source", str(tmp_path)])

    assert result == 0
    output = capsys.readouterr().out
    assert "brand" in output.casefold()
    assert "zoom_background" in output
    assert "Dry-run: no se hizo login ni se subió ningún archivo." in output


def test_execute_requires_environment_credentials(monkeypatch):
    monkeypatch.delenv("IH_DESIGN_USERNAME", raising=False)
    monkeypatch.delenv("IH_DESIGN_PASSWORD", raising=False)

    with pytest.raises(UploadError, match="IH_DESIGN_USERNAME, IH_DESIGN_PASSWORD"):
        execute_upload([], "https://example.invalid")
