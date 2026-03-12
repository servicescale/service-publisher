from __future__ import annotations

import json
from pathlib import Path

from .models import Site


def create_site_manifest(
    site_id: str,
    name: str,
    niche_focus: str,
    target_audience: str,
    brand_tone: str,
    monetization_strategy: str,
    publishing_channels: list[str],
    opportunity_pool: list[dict[str, object]] | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    site = Site(
        id=site_id,
        name=name,
        niche_focus=niche_focus,
        target_audience=target_audience,
        brand_tone=brand_tone,
        monetization_strategy=monetization_strategy,
        publishing_channels=publishing_channels,
        opportunity_pool=opportunity_pool or [],
        metadata=metadata or {},
    )
    return site.to_dict()


def write_site_manifest(path: str | Path, manifest: dict[str, object]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
