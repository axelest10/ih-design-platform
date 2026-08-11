"""Versionado común para previews HTML/SVG de diseños."""
from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from designs.models import Design, DesignVersion

from .renderer import RenderedPreview


def _next_test_number() -> int:
    return (
        Design.objects.filter(test_number__isnull=False).aggregate(maximum=Max("test_number"))[
            "maximum"
        ]
        or 0
    ) + 1


@transaction.atomic
def create_next_version(
    design: Design,
    rendered: RenderedPreview,
) -> tuple[Design, DesignVersion]:
    """Persiste una nueva versión y aplica la regla vigente de revisión/pruebas."""
    design = Design.objects.select_for_update().select_related("brief").get(pk=design.pk)
    next_number = (
        design.versions.aggregate(max_number=Max("number"))["max_number"] or 0
    ) + 1
    version = DesignVersion.objects.create(
        design=design,
        number=next_number,
        template_key=rendered.template_key,
        render_data={**rendered.data, "html": rendered.html, "svg": rendered.svg},
        asset_refs=rendered.asset_refs,
        validation_summary=rendered.validation_summary,
    )

    update_fields = ["status", "updated_at"]
    if design.brief.product_slug and settings.DESIGN_TEST_MODE:
        if design.test_number is None:
            design.test_number = _next_test_number()
            update_fields.append("test_number")
        design.status = Design.Status.SELF_REVIEW
    else:
        design.status = Design.Status.IN_REVIEW
    design.save(update_fields=update_fields)
    return design, version
