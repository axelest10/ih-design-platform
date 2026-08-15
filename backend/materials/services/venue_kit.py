"""Construcción determinista de piezas localizadas para una sede IH."""
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
from designs.services.renderer_presentation import render_presentation_preview

from ..models import MaterialBundleItem, MaterialTemplate
from .catalog import VENUE_KIT_DEFAULT_PRODUCT_SLUGS, venue_kit_products

VENUE_KIT_DELIVERABLES: tuple[dict[str, str], ...] = (
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
    {
        "key": "venue-brochure",
        "label": "Brochure de sede",
        "format": "html",
        "template_key": "brochure-a4-v1",
        "scope": "per-bundle",
    },
    {
        "key": "venue-presentation",
        "label": "Presentación de sede",
        "format": "presentation",
        "template_key": "presentation-16x9-v1",
        "scope": "per-bundle",
    },
)


class VenueKitGenerationError(ValueError):
    """Datos insuficientes, no confirmados o inválidos para un venue-kit."""


def venue_kit_deliverables() -> list[dict[str, str]]:
    return [dict(item) for item in VENUE_KIT_DELIVERABLES]


def _context_value(context: dict[str, Any], key: str, product_slug: str) -> str:
    product_copy = context.get("copy_by_product") or {}
    scoped = product_copy.get(product_slug) or {}
    return str(scoped.get(key) or context.get(key) or "").strip()


def _catalog_product(product_slug: str) -> dict[str, Any]:
    product = next(
        (item for item in venue_kit_products() if item["product_slug"] == product_slug),
        None,
    )
    if product is None:
        raise VenueKitGenerationError(
            f"El producto '{product_slug}' no está disponible en el catálogo activo."
        )
    return product


def _required_context(context: dict[str, Any], product_slug: str) -> dict[str, str]:
    required = {
        key: _context_value(context, key, product_slug)
        for key in ("headline", "body", "cta", "audience", "objective")
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise VenueKitGenerationError(
            "Faltan campos obligatorios en brief_context: " + ", ".join(missing) + "."
        )
    return required


def _validate_branch(bundle) -> dict[str, Any]:
    branch = bundle.branch
    if branch is None:
        raise VenueKitGenerationError("venue-kit requiere seleccionar una sede confirmada.")
    if branch.country and bundle.country and branch.country != bundle.country.upper():
        raise VenueKitGenerationError("La sede y el país del paquete no coinciden.")
    contact_data = branch.official_contact_data or {}
    if contact_data.get("source_status") != "confirmed":
        raise VenueKitGenerationError(
            "Los datos oficiales de esta sede siguen pendientes de confirmación."
        )
    location = contact_data.get("location") or {}
    contact = contact_data.get("contact") or {}
    if not location.get("address") or not contact.get("phone"):
        raise VenueKitGenerationError(
            "La sede confirmada debe tener dirección y teléfono oficiales."
        )
    if not branch.source_url:
        raise VenueKitGenerationError("La sede debe conservar la URL de su fuente oficial.")
    return {
        "code": branch.code,
        "name": branch.name,
        "country": branch.country,
        "city": branch.city,
        "location": location,
        "contact": contact,
        "source_url": branch.source_url,
        "source_status": contact_data.get("source_status"),
        "needs_confirmation": contact_data.get("needs_confirmation", []),
    }


def _validate_logos(context: dict[str, Any], country: str, user) -> tuple[str, list[str]]:
    brand_logo_key = str(context.get("brand_logo_key") or "").strip()
    if not brand_logo_key:
        raise VenueKitGenerationError(
            "El contexto del paquete debe incluir brand_logo_key con un logo IH aprobado."
        )
    if brand_logo_key.startswith("uploaded:"):
        raise VenueKitGenerationError("El logo IH principal debe provenir del catálogo oficial.")
    logo_error = validate_brief_logo_access(brand_logo_key, country, user)
    if logo_error:
        raise VenueKitGenerationError(logo_error)

    additional_logo_keys = [str(key) for key in context.get("additional_logo_keys") or []]
    if len(additional_logo_keys) > 3:
        raise VenueKitGenerationError("Puedes agregar hasta tres logos adicionales por pieza.")
    for key in additional_logo_keys:
        if key.startswith("uploaded:"):
            if not validate_uploaded_logo_access(key.split(":", 1)[1], user):
                raise VenueKitGenerationError(f"No puedes usar el logo subido '{key}'.")
        else:
            error = validate_brief_logo_access(key, country, user)
            if error:
                raise VenueKitGenerationError(error)
    return brand_logo_key, additional_logo_keys


def _next_test_number() -> int:
    return (
        Design.objects.filter(test_number__isnull=False).aggregate(max_number=Max("test_number"))[
            "max_number"
        ]
        or 0
    ) + 1


def _local_body(copy: dict[str, str], venue: dict[str, Any]) -> str:
    location = venue["location"]
    contact = venue["contact"]
    contact_parts = [location["address"], venue["city"], contact["phone"]]
    if contact.get("email"):
        contact_parts.append(contact["email"])
    return f"{copy['body']}\n\n{' · '.join(str(part) for part in contact_parts if part)}"


def _create_design(brief: DesignBrief, *, next_test_number: int) -> Design:
    return Design.objects.create(
        brief=brief,
        status=(
            Design.Status.SELF_REVIEW
            if settings.DESIGN_TEST_MODE
            else Design.Status.IN_REVIEW
        ),
        test_number=next_test_number if settings.DESIGN_TEST_MODE else None,
    )


def _brief_context(
    context: dict[str, Any], venue: dict[str, Any], product_slug: str, deliverable: dict[str, str]
) -> dict[str, Any]:
    return {
        **context,
        "venue": venue,
        "venue_kit": {
            "deliverable_key": deliverable["key"],
            "template_key": deliverable["template_key"],
            "product_slug": product_slug,
            "needs_confirmation": venue["needs_confirmation"],
        },
    }


@transaction.atomic
def generate_venue_kit(
    bundle,
    *,
    user=None,
    review_provider: VisualReviewProvider | None = None,
) -> list[Any]:
    if bundle.material_type.slug != "venue-kit":
        raise VenueKitGenerationError("Solo se puede generar este paquete desde un venue-kit.")
    if bundle.items.exists():
        raise VenueKitGenerationError(
            "Este paquete ya tiene piezas generadas; edítalo antes de generar uno nuevo."
        )

    context = bundle.brief_context or {}
    venue = _validate_branch(bundle)
    brand_logo_key, additional_logo_keys = _validate_logos(context, bundle.country, user)
    product_slugs = bundle.product_slugs or list(VENUE_KIT_DEFAULT_PRODUCT_SLUGS)
    next_test_number = _next_test_number()
    items = []

    social_type = MaterialTemplate.objects.get(key="square-v1").material_type
    social_templates = {
        item["template_key"]: MaterialTemplate.objects.get(
            key=item["template_key"], material_type=social_type, active=True
        )
        for item in VENUE_KIT_DELIVERABLES[:3]
    }
    bundle_templates = {
        item["template_key"]: MaterialTemplate.objects.get(
            key=item["template_key"], active=True
        )
        for item in VENUE_KIT_DELIVERABLES[3:]
    }

    for product_slug in product_slugs:
        product = _catalog_product(product_slug)
        copy = _required_context(context, product_slug)
        body = _local_body(copy, venue)
        product_color_status = "catalogued" if product.get("pillar") else "needs_confirmation"

        for deliverable in VENUE_KIT_DELIVERABLES[:3]:
            template = social_templates[deliverable["template_key"]]
            title = (
                f"{bundle.name} · {venue['name']} · "
                f"{product.get('canonical_name', product_slug)} · {deliverable['label']}"
            )
            brief = DesignBrief.objects.create(
                status=DesignBrief.Status.IN_REVIEW,
                format=deliverable["format"],
                title=title[:180],
                country=bundle.country,
                product_slug=product_slug,
                brand_logo_key=brand_logo_key,
                additional_logo_keys=additional_logo_keys,
                material_type=template.material_type,
                branch=bundle.branch,
                campaign=bundle.campaign,
                audience=copy["audience"],
                objective=copy["objective"],
                requested_message=copy["headline"],
                language=str(context.get("language") or "es"),
                channel=str(context.get("channel") or "local-venue"),
                brief_data=_brief_context(context, venue, product_slug, deliverable),
                constraints={
                    "source": "venue-kit",
                    "template_key": template.key,
                    "partner_logos_are_secondary": True,
                },
                created_by=user if user and user.is_authenticated else None,
            )
            design = _create_design(brief, next_test_number=next_test_number)
            if settings.DESIGN_TEST_MODE:
                next_test_number += 1
            try:
                rendered = render_preview(
                    {
                        "template_key": template.key,
                        "product_slug": product_slug,
                        "headline": copy["headline"],
                        "body": body,
                        "cta": copy["cta"],
                        "eyebrow": str(product.get("canonical_name") or venue["name"]),
                        "logo_name": brand_logo_key,
                        "additional_logo_keys": additional_logo_keys,
                        "background_token": str(context.get("background_token") or "knowledge"),
                        "accent_token": str(context.get("accent_token") or "knowledge"),
                        "text_token": str(context.get("text_token") or "dark_navy"),
                        "_allow_validation_warnings": True,
                    }
                )
            except RenderValidationError as exc:
                raise VenueKitGenerationError(f"{title}: {exc}") from exc
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

    primary_product_slug = product_slugs[0]
    primary_copy = _required_context(context, primary_product_slug)
    for deliverable in VENUE_KIT_DELIVERABLES[3:]:
        template = bundle_templates[deliverable["template_key"]]
        title = f"{bundle.name} · {venue['name']} · {deliverable['label']}"
        brief = DesignBrief.objects.create(
            status=DesignBrief.Status.IN_REVIEW,
            format=deliverable["format"],
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
            requested_message=primary_copy["headline"],
            language=str(context.get("language") or "es"),
            channel="local-venue",
            brief_data=_brief_context(context, venue, primary_product_slug, deliverable),
            constraints={
                "source": "venue-kit",
                "template_key": template.key,
                "partner_logos_are_secondary": True,
            },
            created_by=user if user and user.is_authenticated else None,
        )
        design = _create_design(brief, next_test_number=next_test_number)
        if settings.DESIGN_TEST_MODE:
            next_test_number += 1
        values = {
            "headline": primary_copy["headline"],
            "body": _local_body(primary_copy, venue),
            "cta": primary_copy["cta"],
        }
        try:
            if template.material_type.renderer_family == "document":
                rendered = render_document_preview(
                    {"template_key": template.key, "logo_name": brand_logo_key, **values},
                    material_type=template.material_type,
                )
                output_path = default_storage.save(
                    f"generated-designs/{design.pk}/version-1.pdf",
                    ContentFile(rendered.pdf),
                )
                render_data = {**rendered.data, "pdf_path": output_path}
                asset_refs = [*rendered.asset_refs, output_path]
                validation_summary = rendered.validation_summary
            else:
                rendered = render_presentation_preview(
                    {"template_key": template.key, "logo_name": brand_logo_key, **values},
                    material_type=template.material_type,
                )
                output_path = default_storage.save(
                    f"generated-designs/{design.pk}/version-1.pptx",
                    ContentFile(rendered.pptx),
                )
                render_data = {**rendered.data, "pptx_path": output_path}
                asset_refs = [*rendered.asset_refs, output_path]
                validation_summary = rendered.validation_summary
        except RenderValidationError as exc:
            raise VenueKitGenerationError(f"{title}: {exc}") from exc
        version = DesignVersion.objects.create(
            design=design,
            number=1,
            template_key=template.key,
            render_data=render_data,
            asset_refs=asset_refs,
            validation_summary=validation_summary,
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
