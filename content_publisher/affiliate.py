from __future__ import annotations

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


def build_affiliate_url(
    base_url: str,
    *,
    source: str = "content-publisher",
    medium: str = "blog",
    campaign: str = "",
    content: str = "",
    associate_tag: str = "",
) -> str:
    if not base_url:
        return base_url
    try:
        parsed = urlparse(base_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["utm_source"] = source
        if medium:
            query["utm_medium"] = medium
        if campaign:
            query["utm_campaign"] = campaign
        if content:
            query["utm_content"] = content
        if associate_tag and "amazon.com.au" in parsed.netloc:
            query["tag"] = associate_tag
        return urlunparse(parsed._replace(query=urlencode(query)))
    except Exception:
        return base_url
