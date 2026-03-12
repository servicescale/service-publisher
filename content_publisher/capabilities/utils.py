from __future__ import annotations

from ..seo import tokens


def normalize(value: str) -> str:
    return " ".join(value.lower().split())


def tokenize(value: str) -> list[str]:
    return tokens(value)
