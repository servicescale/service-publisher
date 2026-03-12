from __future__ import annotations

from ..seo import overlap_signal


def evaluate_overlap(topic: str, existing_topics: list[str]) -> dict[str, object]:
    return overlap_signal(topic, existing_topics)
