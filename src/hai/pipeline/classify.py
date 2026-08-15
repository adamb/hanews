from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from hai.config import Settings, get_settings, load_scoring, load_sources
from hai.db import dump_json, record_decision, story_items, update_story
from hai.llm.client import LLMError, classify_with_model
from hai.llm.schemas import Classification
from hai.pipeline.score import (
    apply_keyword_gate,
    authority_from_source,
    overall_score,
    recency_novelty_penalty,
)

Classifier = Callable[..., Classification]


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    except ValueError:
        return None


def _source_map(settings: Settings | None = None) -> dict[str, Any]:
    return {source.id: source for source in load_sources(settings)}


def pending_stories(
    conn: sqlite3.Connection,
    *,
    recency_days: int,
    limit: int,
    now: datetime | None = None,
) -> list[sqlite3.Row]:
    current = now or datetime.now(timezone.utc)
    cutoff = (current - timedelta(days=recency_days)).isoformat()
    return list(
        conn.execute(
            """
            SELECT s.*, i.published_at AS primary_published_at, i.title AS primary_title
            FROM stories s
            JOIN items i ON i.id = s.primary_item_id
            WHERE s.decision IS NULL
              AND (
                    i.published_at IS NULL
                    OR i.published_at >= ?
                    OR s.created_at >= ?
              )
            ORDER BY COALESCE(s.authority_score, 0) DESC,
                     i.published_at IS NULL,
                     i.published_at DESC
            LIMIT ?
            """,
            (cutoff, cutoff, limit),
        )
    )


def classify_story(
    conn: sqlite3.Connection,
    story: sqlite3.Row,
    *,
    run_id: int | None,
    settings: Settings | None = None,
    classifier: Classifier | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    scoring = load_scoring(settings)
    sources = _source_map(settings)
    items = story_items(conn, int(story["id"]))
    if not items:
        return {"status": "skipped", "reason": "no_items"}

    primary = items[0]
    source = sources.get(primary["source_id"])
    authority = authority_from_source(source.authority if source else 0.5)
    haystack = f"{primary['title']}\n{primary['raw_text'] or ''}"
    gate_cfg = scoring.get("keyword_gate") or {}
    skip_gate_authority = float(gate_cfg.get("min_authority_to_skip", 0.85))
    source_authority = source.authority if source else 0.5

    if gate_cfg.get("enabled", True) and source_authority < skip_gate_authority:
        hit = apply_keyword_gate(haystack, list(gate_cfg.get("keywords") or []))
        if hit is None:
            update_story(
                conn,
                int(story["id"]),
                {
                    "decision": "reject",
                    "decision_reason": "keyword_gate",
                    "relevance_score": 10,
                    "novelty_score": 0,
                    "importance_score": 10,
                    "authority_score": authority,
                    "personal_interest_score": 5,
                    "overall_score": overall_score(
                        relevance=10,
                        novelty=0,
                        importance=10,
                        authority=authority,
                        personal_interest=5,
                        weights=scoring.get("weights"),
                    ),
                    "summary": primary["title"],
                },
            )
            record_decision(
                conn,
                decision_type="keyword_gate",
                run_id=run_id,
                story_id=int(story["id"]),
                item_id=int(primary["id"]),
                input_data={"title": primary["title"], "url": primary["url"]},
                output_data={"decision": "reject", "reason": "keyword_gate"},
                model=None,
            )
            return {"status": "rejected", "reason": "keyword_gate"}

    classify_fn = classifier or classify_with_model
    try:
        result = classify_fn(
            title=primary["title"],
            url=primary["url"],
            source_name=source.name if source else primary["source_id"],
            source_authority=source_authority,
            published_at=primary["published_at"],
            text=primary["raw_text"] or "",
            source_categories=source.categories if source else [],
            settings=settings,
        )
    except TypeError:
        # Allow test doubles that do not accept settings=
        result = classify_fn(
            title=primary["title"],
            url=primary["url"],
            source_name=source.name if source else primary["source_id"],
            source_authority=source_authority,
            published_at=primary["published_at"],
            text=primary["raw_text"] or "",
            source_categories=source.categories if source else [],
        )
    except LLMError as exc:
        record_decision(
            conn,
            decision_type="classify_error",
            run_id=run_id,
            story_id=int(story["id"]),
            item_id=int(primary["id"]),
            input_data={"title": primary["title"], "url": primary["url"]},
            output_data={"error": str(exc)},
            model=settings.xai_model,
        )
        return {"status": "error", "reason": str(exc)}

    published = _parse_dt(primary["published_at"])
    novelty = min(result.novelty_score, recency_novelty_penalty(published))
    keep_threshold = float(scoring.get("keep_threshold", 50))
    computed = overall_score(
        relevance=result.relevance_score,
        novelty=novelty,
        importance=result.importance_score,
        authority=authority,
        personal_interest=result.personal_interest_score,
        weights=scoring.get("weights"),
    )
    decision = result.decision
    reason = result.reason
    if computed < keep_threshold and decision == "keep":
        decision = "reject"
        reason = f"overall_score {computed} below keep_threshold {keep_threshold}; {reason}"

    update_story(
        conn,
        int(story["id"]),
        {
            "topic": result.topics[0] if result.topics else None,
            "topics_json": dump_json(result.topics),
            "summary": result.summary,
            "relevance_score": result.relevance_score,
            "novelty_score": novelty,
            "importance_score": result.importance_score,
            "authority_score": authority,
            "personal_interest_score": result.personal_interest_score,
            "overall_score": computed,
            "decision": decision,
            "decision_reason": reason,
            "why_it_matters": result.why_it_matters,
            "why_you_care": result.why_you_care,
            "claims_json": dump_json(result.claims_to_verify),
        },
    )
    record_decision(
        conn,
        decision_type="classify",
        run_id=run_id,
        story_id=int(story["id"]),
        item_id=int(primary["id"]),
        input_data={"title": primary["title"], "url": primary["url"]},
        output_data=result.model_dump(),
        model=settings.xai_model,
    )
    return {"status": decision, "reason": reason, "overall_score": computed}
