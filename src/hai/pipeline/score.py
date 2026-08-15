from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_WEIGHTS = {
    "relevance": 0.25,
    "novelty": 0.20,
    "importance": 0.20,
    "authority": 0.15,
    "personal_interest": 0.20,
}


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def overall_score(
    *,
    relevance: float,
    novelty: float,
    importance: float,
    authority: float,
    personal_interest: float,
    weights: dict[str, float] | None = None,
) -> float:
    used = weights or DEFAULT_WEIGHTS
    total = (
        clamp_score(relevance) * used.get("relevance", 0)
        + clamp_score(novelty) * used.get("novelty", 0)
        + clamp_score(importance) * used.get("importance", 0)
        + clamp_score(authority) * used.get("authority", 0)
        + clamp_score(personal_interest) * used.get("personal_interest", 0)
    )
    return round(clamp_score(total), 2)


def authority_from_source(authority: float) -> float:
    return clamp_score(authority * 100.0)


def recency_novelty_penalty(published_at: datetime | None, now: datetime | None = None) -> float:
    """Return a 0-100 novelty cap based on age. Newer is higher."""
    if published_at is None:
        return 70.0
    current = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (current - published_at).total_seconds() / 86400.0)
    if age_days <= 2:
        return 100.0
    if age_days <= 7:
        return 85.0
    if age_days <= 14:
        return 65.0
    if age_days <= 30:
        return 40.0
    return 20.0


def apply_keyword_gate(text: str, keywords: list[str]) -> str | None:
    haystack = (text or "").casefold()
    for keyword in keywords:
        if keyword.casefold() in haystack:
            return keyword
    return None
