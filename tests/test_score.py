from datetime import datetime, timedelta, timezone

from hai.pipeline.score import (
    apply_keyword_gate,
    authority_from_source,
    clamp_score,
    overall_score,
    recency_novelty_penalty,
)


def test_overall_score_uses_readme_weights() -> None:
    score = overall_score(
        relevance=100,
        novelty=0,
        importance=0,
        authority=0,
        personal_interest=0,
    )
    assert score == 25.0


def test_overall_score_clamps() -> None:
    assert clamp_score(140) == 100
    assert overall_score(
        relevance=200,
        novelty=200,
        importance=200,
        authority=200,
        personal_interest=200,
    ) == 100


def test_authority_from_source() -> None:
    assert authority_from_source(1.0) == 100
    assert authority_from_source(0.6) == 60


def test_keyword_gate() -> None:
    assert apply_keyword_gate("New Matter-over-Thread sensor", ["matter"]) == "matter"
    assert apply_keyword_gate("iPhone rumor roundup", ["matter", "thread"]) is None


def test_recency_novelty_penalty() -> None:
    now = datetime(2026, 8, 15, tzinfo=timezone.utc)
    fresh = now - timedelta(hours=12)
    old = now - timedelta(days=40)
    assert recency_novelty_penalty(fresh, now) == 100
    assert recency_novelty_penalty(old, now) == 20
