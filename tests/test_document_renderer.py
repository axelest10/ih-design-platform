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

FORMAL_DOCUMENT_PAYLOADS = {
    "letter-a4-v1": {
        "sender": "International House México",
        "recipient": "Dirección académica",
        "body": "Compartimos la propuesta educativa preparada para su comunidad escolar.",
        "signature": "Equipo International House",
    },
    "announcement-a4-v1": {
        "headline": "Nueva fecha informativa",
        "date": "15 de septiembre",
        "body": "Conoce los programas disponibles para estudiantes y docentes.",
        "contact": "admisiones@ihmexico.com",
    },
    "flyer-a4-v1": {
        "headline": "Inglés para tu comunidad",
        "subtitle": "Programas internacionales para cada etapa",
        "body": "Acompañamos a estudiantes y docentes con objetivos claros.",
        "cta": "Solicita información",
        "contact": "admisiones@ihmexico.com",
    },
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
@pytest.mark.parametrize("template_key", FORMAL_DOCUMENT_PAYLOADS)
def test_document_renderer_supports_school_formal_layouts(template_key):
    material_type = MaterialType.objects.get(slug="school-documents")
    payload = {
        "template_key": template_key,
        "logo_name": "ih-mexico-classic-png",
        **FORMAL_DOCUMENT_PAYLOADS[template_key],
    }

    rendered = render_document_preview(payload, material_type=material_type)

    assert rendered.pdf.startswith(b"%PDF-")
    assert rendered.template_key == template_key
    assert rendered.data["layout"] in {"formal-letter", "announcement", "flyer"}
    assert rendered.validation_summary["status"] == "passed"


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
def test_document_preview_returns_400_for_invalid_render_payload():
    material_type = MaterialType.objects.get(slug="brochure")
    brief = DesignBrief.objects.create(
        title="Brochure inválido",
        format=DesignBrief.Format.HTML,
        material_type=material_type,
        audience="Escuelas",
        objective="Validar errores de renderizado",
    )
    design = Design.objects.create(brief=brief)
    incomplete_payload = {**DOCUMENT_PAYLOAD}
    incomplete_payload.pop("body")

    response = APIClient().post(
        f"/api/v1/designs/{design.pk}/preview/",
        incomplete_payload,
        format="json",
    )

    assert response.status_code == 400
    assert "'body' es obligatorio" in response.json()["detail"]


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
