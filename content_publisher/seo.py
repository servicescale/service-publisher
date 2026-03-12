from __future__ import annotations

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
    "your",
    "you",
}


def normalize_text(value: str = "") -> str:
    chars: list[str] = []
    previous_space = False
    for char in str(value).lower():
        if char.isalnum():
            chars.append(char)
            previous_space = False
        elif not previous_space:
            chars.append(" ")
            previous_space = True
    return "".join(chars).strip()


def tokens(value: str = "") -> list[str]:
    return [token for token in normalize_text(value).split(" ") if token and token not in STOPWORDS]


def jaccard_similarity(a: str = "", b: str = "") -> float:
    a_tokens = set(tokens(a))
    b_tokens = set(tokens(b))
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return intersection / union if union else 0.0


def overlap_signal(topic: str, existing_topics: list[str]) -> dict[str, object]:
    scored = sorted(
        (
            {
                "topic": existing,
                "similarity": round(jaccard_similarity(topic, existing), 3),
            }
            for existing in existing_topics
        ),
        key=lambda item: item["similarity"],
        reverse=True,
    )
    top = scored[0] if scored else None
    severe = bool(top and top["similarity"] >= 0.82)
    warning = bool(top and not severe and top["similarity"] >= 0.62)
    return {
        "should_skip": severe,
        "has_warning": warning,
        "warning": (
            f'High overlap risk with "{top["topic"]}" ({int(float(top["similarity"]) * 100)}% similarity).'
            if warning and top
            else None
        ),
        "nearest_matches": scored[:3],
    }
