from __future__ import annotations

from ..affiliate import build_affiliate_url
from ..models import Product, Site


def rewrite_product_url(site: Site, title: str, raw_url: str) -> str:
    return build_affiliate_url(
        raw_url,
        source=str(site.metadata.get("affiliate_source", site.id)),
        medium="catalog",
        campaign=site.id,
        content=title.lower().replace(" ", "-"),
        associate_tag=str(site.metadata.get("associate_tag", "")),
    )


def decorate_product(site: Site, product: Product) -> Product:
    product.url = rewrite_product_url(site, product.title, product.url)
    return product
