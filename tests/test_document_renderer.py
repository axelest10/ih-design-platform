import pytest
from django.core.files.storage import FileSystemStorage
from rest_framework.test import APIClient

from briefs.models import DesignBrief
from designs.models import Design, DesignVersion
from designs.services.renderer import RenderValidationError
from designs.services.renderer_document import render_document_preview
from materials.models import MaterialType

DOCUMENT_PAYLOAD = {
    "template_key": "brochure-a4-v1",
    "headline": "Inglés que conecta con el mundo",
    "body": (
        "Programas creados para acompañar a estudiantes, docentes y comunidades educativas "
        "con una metodología internacional y objetivos claros."
    ),
    "cta": "Conoce nuestros programas",
    "logo_name": "ih-mexico-classic-png",
}


@pytest.mark.django_db
def test_document_renderer_generates_valid_pdf_from_registered_template():
    material_type = MaterialType.objects.get(slug="brochure")

    rendered = render_document_preview(DOCUMENT_PAYLOAD, material_type=material_type)

    assert rendered.pdf.startswith(b"%PDF-")
    assert rendered.template_key == "brochure-a4-v1"
    assert rendered.validation_summary["status"] == "passed"
    assert rendered.asset_refs == ["ih-mexico-classic-png"]


@pytest.mark.django_db
def test_document_renderer_rejects_payload_missing_required_field():
    material_type = MaterialType.objects.get(slug="brochure")
    incomplete = {**DOCUMENT_PAYLOAD}
    incomplete.pop("body")

    with pytest.raises(RenderValidationError, match="'body' es obligatorio"):
        render_document_preview(incomplete, material_type=material_type)


@pytest.mark.django_db
def test_document_preview_saves_pdf_with_configured_storage(tmp_path, monkeypatch):
    storage = FileSystemStorage(location=tmp_path, base_url="/media/")
    monkeypatch.setattr("designs.views.default_storage", storage)
    material_type = MaterialType.objects.get(slug="brochure")
    brief = DesignBrief.objects.create(
        title="Brochure piloto",
        format=DesignBrief.Format.HTML,
        material_type=material_type,
        audience="Escuelas",
        objective="Presentar la oferta educativa",
    )
    design = Design.objects.create(brief=brief)

    response = APIClient().post(
        f"/api/v1/designs/{design.pk}/preview/",
        DOCUMENT_PAYLOAD,
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["preview"]["pdf_url"].endswith(".pdf")
    version = DesignVersion.objects.get(design=design)
    pdf_path = version.render_data["pdf_path"]
    assert storage.exists(pdf_path)
    with storage.open(pdf_path, "rb") as pdf_file:
        assert pdf_file.read(5) == b"%PDF-"
    assert pdf_path in version.asset_refs
    assert "html" not in version.render_data
    assert "svg" not in version.render_data


@pytest.mark.django_db
def test_html_svg_dispatch_remains_unchanged_for_social_post():
    material_type = MaterialType.objects.get(slug="social-post")
    brief = DesignBrief.objects.create(
        title="Social post existente",
        format=DesignBrief.Format.SQUARE,
        material_type=material_type,
        audience="Estudiantes",
        objective="Conservar el renderer existente",
    )
    design = Design.objects.create(brief=brief)

    response = APIClient().post(
        f"/api/v1/designs/{design.pk}/preview/",
        {"template_key": "square-v1", "headline": "Título", "body": "Cuerpo"},
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert response.json()["preview"]["html"].startswith("<!doctype html>")
    assert response.json()["preview"]["svg"].startswith("<svg")
    version = DesignVersion.objects.get(design=design)
    assert version.render_data["html"].startswith("<!doctype html>")
    assert version.render_data["svg"].startswith("<svg")
    assert "pdf_path" not in version.render_data
