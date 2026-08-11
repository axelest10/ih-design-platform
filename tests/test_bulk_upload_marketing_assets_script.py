import pytest
from scripts import bulk_upload_marketing_assets as bulk_upload
from scripts.bulk_upload_marketing_assets import (
    AssetCandidate,
    UploadError,
    _upload_batch,
    execute_upload,
    fetch_all_marketing_assets,
    main,
    scan_assets,
)


def test_scan_assets_infers_brand_country_category_and_label(tmp_path):
    source = tmp_path / "inventario"
    files = (
        source / "INTERNATIONAL HOUSE" / "México" / "Fotos de perfil" / "IH-MX_perfil.png",
        source / "INTERNATIONAL HOUSE" / "Colombia" / "Desktop" / "COL 1-100.jpg",
        source / "IELTS" / "Firmas electrónicas" / "IELTS_FIRMA.docx",
        source / "INTERNATIONAL HOUSE" / "Chile" / "Foto Whatsapp" / "whatsapp.png",
        source / "IELTS" / "Templates Ppt" / "plantilla.pptx",
        source / "INTERNATIONAL HOUSE" / "Perú" / "Foto perfil Whatsapp" / "perfil-wa.png",
        source / "INTERNATIONAL HOUSE" / "MX" / "Fotos perfil Whatsapp" / "perfiles-wa.png",
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
        "IH MX Perfil",
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
    assert by_name["whatsapp.png"].category == "foto_perfil"
    assert by_name["plantilla.pptx"].category == "template_ppt"
    assert by_name["perfil-wa.png"].category == "foto_perfil"
    assert by_name["perfiles-wa.png"].category == "foto_perfil"
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


def test_upload_batch_sends_https_referer_with_csrf_header(tmp_path):
    file_path = tmp_path / "perfil.png"
    file_path.write_bytes(b"png")
    candidate = AssetCandidate(
        path=file_path,
        relative_path="perfil.png",
        brand="ih",
        country="MX",
        category="foto_perfil",
        label="perfil",
    )

    class StubSession:
        cookies = {"csrftoken": "csrf-token"}

        def post(self, url, **kwargs):
            self.url = url
            self.kwargs = kwargs
            return "response"

    session = StubSession()

    response = _upload_batch(session, "https://example.test", [candidate])

    assert response == "response"
    assert session.url == "https://example.test/api/v1/materials/marketing-assets/bulk/"
    assert session.kwargs["headers"] == {
        "X-CSRFToken": "csrf-token",
        "Referer": "https://example.test/",
    }


def test_fetch_all_marketing_assets_follows_pagination():
    class StubResponse:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class StubSession:
        def __init__(self):
            self.urls = []

        def get(self, url, **kwargs):
            self.urls.append(url)
            if len(self.urls) == 1:
                return StubResponse(
                    {
                        "results": [{"id": 1}],
                        "next": "/api/v1/marketing-assets/?page=2",
                    }
                )
            return StubResponse({"results": [{"id": 2}], "next": None})

    class StubRequests:
        RequestException = OSError

    session = StubSession()

    assets = fetch_all_marketing_assets(
        session,
        "https://example.test",
        StubRequests,
    )

    assert [asset["id"] for asset in assets] == [1, 2]
    assert session.urls == [
        "https://example.test/api/v1/marketing-assets/",
        "https://example.test/api/v1/marketing-assets/?page=2",
    ]


def test_execute_upload_omits_assets_that_already_exist(
    tmp_path, monkeypatch, capsys
):
    existing_path = tmp_path / "existente.png"
    new_path = tmp_path / "nuevo.png"
    existing_path.write_bytes(b"existing")
    new_path.write_bytes(b"new")
    candidates = [
        AssetCandidate(
            path=existing_path,
            relative_path=existing_path.name,
            brand="ih",
            country="MX",
            category="foto_perfil",
            label="Existente",
        ),
        AssetCandidate(
            path=new_path,
            relative_path=new_path.name,
            brand="ih",
            country="MX",
            category="foto_perfil",
            label="Nuevo",
        ),
    ]

    class StubResponse:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class StubSession:
        def __init__(self):
            self.cookies = {}
            self.uploaded = []

        def get(self, url, **kwargs):
            assert url == "https://example.test/api/v1/marketing-assets/"
            return StubResponse(
                [
                    {
                        "id": 1,
                        "brand": "ih",
                        "country": "MX",
                        "category": "foto_perfil",
                        "label": "Existente",
                    }
                ]
            )

        def post(self, url, **kwargs):
            if url.endswith("/api/v1/auth/login/"):
                self.cookies["csrftoken"] = "csrf-token"
                return StubResponse({"authenticated": True})
            self.uploaded.extend(file_data[1][0] for file_data in kwargs["files"])
            return StubResponse(
                {
                    "created_count": len(kwargs["files"]),
                    "failed_count": 0,
                    "created": [],
                    "failed": [],
                }
            )

    class StubRequests:
        RequestException = OSError

        def __init__(self, session):
            self.session = session

        def Session(self):
            return self.session

    session = StubSession()
    monkeypatch.setenv("IH_DESIGN_USERNAME", "admin")
    monkeypatch.setenv("IH_DESIGN_PASSWORD", "secret-password")
    monkeypatch.setattr(
        bulk_upload,
        "_requests_module",
        lambda: StubRequests(session),
    )

    result = bulk_upload.execute_upload(candidates, "https://example.test")

    assert result == 0
    assert session.uploaded == ["nuevo.png"]
    output = capsys.readouterr().out
    assert "existente.png: ya existe en la plataforma, omitido" in output
    assert "ya_existentes=1" in output
