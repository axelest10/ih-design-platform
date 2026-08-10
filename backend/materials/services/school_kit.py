"""Construcción determinista del primer paquete de marketing para colegios."""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Max

from ai.services import VisualReviewProvider, run_automatic_design_review
from briefs.models import DesignBrief
from briefs.services.options import validate_brief_logo_access, validate_uploaded_logo_access
from designs.models import Design, DesignVersion
from designs.services.renderer import RenderValidationError, render_preview
from designs.services.renderer_document import render_document_preview

from ..models import MaterialBundleItem, MaterialTemplate
from .catalog import school_kit_products

SCHOOL_KIT_DELIVERABLES: tuple[dict[str, str], ...] = (
    {
        "key": "hero-square",
        "label": "Pieza principal cuadrada",
        "format": "square",
        "template_key": "square-v1",
        "scope": "per-product",
    },
    {
        "key": "story-call-to-action",
        "label": "Story con llamada a la acción",
        "format": "story",
        "template_key": "story-v1",
        "scope": "per-product",
    },
    {
        "key": "portrait-information",
        "label": "Pieza vertical informativa",
        "format": "portrait",
        "template_key": "portrait-v1",
        "scope": "per-product",
    },
)

SCHOOL_KIT_FORMAL_DELIVERABLES: tuple[dict[str, str], ...] = (
    {
        "key": "formal-letter",
        "label": "Carta formal con membrete",
        "format": "html",
        "template_key": "letter-a4-v1",
        "scope": "per-bundle",
    },
    {
        "key": "school-announcement",
        "label": "Anuncio para la comunidad escolar",
        "format": "html",
        "template_key": "announcement-a4-v1",
        "scope": "per-bundle",
    },
    {
        "key": "general-flyer",
        "label": "Flyer informativo general",
        "format": "html",
        "template_key": "flyer-a4-v1",
        "scope": "per-bundle",
    },
)


class SchoolKitGenerationError(ValueError):
    """Datos insuficientes o inválidos para generar las piezas de un school-kit."""


def school_kit_deliverables() -> list[dict[str, str]]:
    """Devuelve el contenido inicial aprobado para cada producto del paquete."""
    return [
        *(dict(item) for item in SCHOOL_KIT_DELIVERABLES),
        *(dict(item) for item in SCHOOL_KIT_FORMAL_DELIVERABLES),
    ]


def _context_value(context: dict[str, Any], key: str, product_slug: str) -> str:
    product_copy = context.get("copy_by_product") or {}
    scoped = product_copy.get(product_slug) or {}
    return str(scoped.get(key) or context.get(key) or "").strip()


def _catalog_product(product_slug: str, country: str) -> dict[str, Any]:
    product = next(
        (
            item
            for item in school_kit_products(country=country)
            if item["product_slug"] == product_slug
        ),
        None,
    )
    if product is None:
        raise SchoolKitGenerationError(
            f"El producto '{product_slug}' no está disponible para el país '{country}'."
        )
    return product


def _validate_logos(context: dict[str, Any], country: str, user) -> tuple[str, list[str]]:
    brand_logo_key = str(context.get("brand_logo_key") or "").strip()
    if not brand_logo_key:
        raise SchoolKitGenerationError(
            "El contexto del paquete debe incluir brand_logo_key con un logo IH aprobado."
        )
    if brand_logo_key.startswith("uploaded:"):
        raise SchoolKitGenerationError("El logo IH principal debe provenir del catálogo oficial.")
    logo_error = validate_brief_logo_access(brand_logo_key, country, user)
    if logo_error:
        raise SchoolKitGenerationError(logo_error)

    additional_logo_keys = [str(key) for key in context.get("additional_logo_keys") or []]
    if len(additional_logo_keys) > 3:
        raise SchoolKitGenerationError("Puedes agregar hasta tres logos adicionales por pieza.")
    for key in additional_logo_keys:
        if key.startswith("uploaded:"):
            if not validate_uploaded_logo_access(key.split(":", 1)[1], user):
                raise SchoolKitGenerationError(f"No puedes usar el logo subido '{key}'.")
        else:
            error = validate_brief_logo_access(key, country, user)
            if error:
                raise SchoolKitGenerationError(error)
    return brand_logo_key, additional_logo_keys


def _next_test_number() -> int:
    return (
        Design.objects.filter(test_number__isnull=False).aggregate(max_number=Max("test_number"))[
            "max_number"
        ]
        or 0
    ) + 1


def _required_context(context: dict[str, Any], product_slug: str) -> dict[str, str]:
    required = {
        key: _context_value(context, key, product_slug)
        for key in ("headline", "body", "cta", "audience", "objective")
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise SchoolKitGenerationError(
            "Faltan campos obligatorios en brief_context: " + ", ".join(missing) + "."
        )
    return required


def _formal_document_values(
    template_key: str,
    context: dict[str, Any],
    copy: dict[str, str],
) -> dict[str, str]:
    sender = str(context.get("sender") or "International House").strip()
    contact = str(context.get("contact") or copy["cta"]).strip()
    if template_key == "letter-a4-v1":
        return {
            "sender": sender,
            "recipient": str(context.get("recipient") or copy["audience"]).strip(),
            "body": copy["body"],
            "signature": str(context.get("signature") or sender).strip(),
        }
    if template_key == "announcement-a4-v1":
        return {
            "headline": copy["headline"],
            "date": str(
                context.get("date") or context.get("campaign_info") or "Fecha por confirmar"
            ).strip(),
            "body": copy["body"],
            "contact": contact,
        }
    return {
        "headline": copy["headline"],
        "subtitle": str(context.get("subtitle") or copy["objective"]).strip(),
        "body": copy["body"],
        "cta": copy["cta"],
        "contact": contact,
    }


@transaction.atomic
def generate_school_kit(
    bundle,
    *,
    user=None,
    review_provider: VisualReviewProvider | None = None,
) -> list[Any]:
    """Crea briefs, diseños, versiones HTML/SVG y estados de revisión por pieza."""
    if bundle.material_type.slug != "school-kit":
        raise SchoolKitGenerationError("Solo se puede generar este paquete desde un school-kit.")
    if bundle.items.exists():
        raise SchoolKitGenerationError(
            "Este paquete ya tiene piezas generadas; edítalo antes de generar uno nuevo."
        )

    context = bundle.brief_context or {}
    brand_logo_key, additional_logo_keys = _validate_logos(context, bundle.country, user)
    next_test_number = _next_test_number()
    items = []

    for product_slug in bundle.product_slugs:
        product = _catalog_product(product_slug, bundle.country)
        copy = _required_context(context, product_slug)
        product_color_status = (
            "catalogued" if product.get("pillar") else "needs_confirmation"
        )

        for deliverable in SCHOOL_KIT_DELIVERABLES:
            title = (
                f"{bundle.name} · {product.get('canonical_name', product_slug)} · "
                f"{deliverable['label']}"
            )
            brief = DesignBrief.objects.create(
                status=DesignBrief.Status.IN_REVIEW,
                format=deliverable["format"],
                title=title[:180],
                country=bundle.country,
                product_slug=product_slug,
                brand_logo_key=brand_logo_key,
                additional_logo_keys=additional_logo_keys,
                branch=bundle.branch,
                campaign=bundle.campaign,
                audience=copy["audience"],
                objective=copy["objective"],
                requested_message=copy["headline"],
                language=str(context.get("language") or "es"),
                channel=str(context.get("channel") or "instagram"),
                brief_data={
                    **context,
                    "school_kit": {
                        "bundle_id": str(bundle.pk),
                        "deliverable_key": deliverable["key"],
                        "template_key": deliverable["template_key"],
                        "product_color_status": product_color_status,
                    },
                },
                constraints={
                    "source": "school-kit",
                    "template_key": deliverable["template_key"],
                    "partner_logos_are_secondary": True,
                },
                created_by=user if user and user.is_authenticated else None,
            )
            design = Design.objects.create(
                brief=brief,
                status=(
                    Design.Status.SELF_REVIEW
                    if settings.DESIGN_TEST_MODE
                    else Design.Status.IN_REVIEW
                ),
                test_number=next_test_number if settings.DESIGN_TEST_MODE else None,
            )
            if settings.DESIGN_TEST_MODE:
                next_test_number += 1

            render_payload = {
                "template_key": deliverable["template_key"],
                "product_slug": product_slug,
                "headline": copy["headline"],
                "body": copy["body"],
                "cta": copy["cta"],
                "eyebrow": str(
                    context.get("eyebrow")
                    or product.get("canonical_name")
                    or "International House"
                ),
                "logo_name": brand_logo_key,
                "additional_logo_keys": additional_logo_keys,
                "background_token": str(context.get("background_token") or "knowledge"),
                "accent_token": str(context.get("accent_token") or "knowledge"),
                "text_token": str(context.get("text_token") or "dark_navy"),
                "_allow_validation_warnings": True,
            }
            try:
                rendered = render_preview(render_payload)
            except RenderValidationError as exc:
                raise SchoolKitGenerationError(f"{title}: {exc}") from exc

            version = DesignVersion.objects.create(
                design=design,
                number=1,
                template_key=rendered.template_key,
                render_data={
                    **rendered.data,
                    "html": rendered.html,
                    "svg": rendered.svg,
                    "product_color_status": product_color_status,
                },
                asset_refs=rendered.asset_refs,
                validation_summary=rendered.validation_summary,
            )
            run_automatic_design_review(version, provider=review_provider)
            items.append(
                MaterialBundleItem.objects.create(
                    bundle=bundle,
                    brief=brief,
                    deliverable_key=f"{product_slug}-{deliverable['key']}",
                    sort_order=len(items),
                )
            )

    # Los documentos institucionales describen el paquete completo; generarlos una sola vez
    # evita duplicados cuando el colegio selecciona varios productos.
    primary_product_slug = bundle.product_slugs[0]
    primary_copy = _required_context(context, primary_product_slug)
    for deliverable in SCHOOL_KIT_FORMAL_DELIVERABLES:
        template = MaterialTemplate.objects.select_related("material_type").get(
            key=deliverable["template_key"],
            active=True,
        )
        values = _formal_document_values(template.key, context, primary_copy)
        title = f"{bundle.name} · {deliverable['label']}"
        brief = DesignBrief.objects.create(
            status=DesignBrief.Status.IN_REVIEW,
            format=DesignBrief.Format.HTML,
            title=title[:180],
            country=bundle.country,
            product_slug=primary_product_slug,
            brand_logo_key=brand_logo_key,
            additional_logo_keys=additional_logo_keys,
            material_type=template.material_type,
            branch=bundle.branch,
            campaign=bundle.campaign,
            audience=primary_copy["audience"],
            objective=primary_copy["objective"],
            requested_message=values.get("headline") or values.get("body", "")[:180],
            language=str(context.get("language") or "es"),
            channel="school",
            brief_data={
                **context,
                "school_kit": {
                    "bundle_id": str(bundle.pk),
                    "deliverable_key": deliverable["key"],
                    "template_key": template.key,
                    "scope": "per-bundle",
                },
                "content": values,
            },
            constraints={
                "source": "school-kit",
                "template_key": template.key,
                "partner_logos_are_secondary": True,
            },
            created_by=user if user and user.is_authenticated else None,
        )
        design = Design.objects.create(
            brief=brief,
            status=(
                Design.Status.SELF_REVIEW
                if settings.DESIGN_TEST_MODE
                else Design.Status.IN_REVIEW
            ),
            test_number=next_test_number if settings.DESIGN_TEST_MODE else None,
        )
        if settings.DESIGN_TEST_MODE:
            next_test_number += 1
        try:
            rendered = render_document_preview(
                {"template_key": template.key, "logo_name": brand_logo_key, **values},
                material_type=template.material_type,
            )
        except RenderValidationError as exc:
            raise SchoolKitGenerationError(f"{title}: {exc}") from exc
        pdf_path = default_storage.save(
            f"generated-designs/{design.pk}/version-1.pdf",
            ContentFile(rendered.pdf),
        )
        version = DesignVersion.objects.create(
            design=design,
            number=1,
            template_key=template.key,
            render_data={**rendered.data, "pdf_path": pdf_path},
            asset_refs=[*rendered.asset_refs, pdf_path],
            validation_summary=rendered.validation_summary,
        )
        run_automatic_design_review(version, provider=review_provider)
        items.append(
            MaterialBundleItem.objects.create(
                bundle=bundle,
                brief=brief,
                deliverable_key=deliverable["key"],
                sort_order=len(items),
            )
        )

    bundle.status = bundle.Status.IN_REVIEW
    bundle.save(update_fields=["status", "updated_at"])
    return items
