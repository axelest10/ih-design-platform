from django import template

from common.frontend_assets import versioned_asset_url

register = template.Library()


@register.simple_tag
def asset_url(path: str) -> str:
    return versioned_asset_url(path)
