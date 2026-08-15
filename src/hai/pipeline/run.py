from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from hai.config import Settings, get_settings, github_token, load_scoring, load_sources
from hai.db import (
    dump_json,
    finish_run,
    get_item_by_source_key,
    insert_item,
    insert_story,
    iso,
    link_item,
    record_decision,
    session,
    start_run,
)
from hai.digest.generate import today_in_tz, write_digest
from hai.discovery.base import UnknownSourceType, discover_source
from hai.gitutil import GitError, push_digest
from hai.models import Source
from hai.pipeline.classify import classify_story, pending_stories
from hai.pipeline.dedupe import find_duplicate_story
from hai.pipeline.normalize import normalized_item_fields
from hai.pipeline.score import authority_from_source

log = logging.getLogger("hai")

Classifier = Callable[..., Any]


def _within_days(published_at: str | None, days: int, now: datetime) -> bool:
    if not published_at:
        return True
    try:
        value = datetime.fromisoformat(published_at)
    except ValueError:
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return value >= current - timedelta(days=days)


def ingest_source(
    conn,
    source: Source,
    *,
    run_id: int,
    token: str,
    recency_days: int,
    now: datetime,
) -> dict[str, int]:
    stats = Counter()
    try:
        raw_items = discover_source(source, github_token=token)
    except UnknownSourceType as exc:
        record_decision(
            conn,
            decision_type="source_error",
            run_id=run_id,
            input_data={"source_id": source.id},
            output_data={"error": str(exc)},
        )
        stats["source_errors"] += 1
        log.warning("Source %s skipped: %s", source.id, exc)
        return stats
    except Exception as exc:  # noqa: BLE001 - isolate source failures
        record_decision(
            conn,
            decision_type="source_error",
            run_id=run_id,
            input_data={"source_id": source.id},
            output_data={"error": str(exc)},
        )
        stats["source_errors"] += 1
        log.warning("Source %s failed: %s", source.id, exc)
        return stats

    stats["fetched"] = len(raw_items)
    for raw in raw_items:
        existing = get_item_by_source_key(conn, raw.source_id, raw.source_item_id)
        if existing:
            stats["already_seen"] += 1
            continue
        fields = normalized_item_fields(raw)
        fields["raw_metadata_json"] = dump_json(raw.raw_metadata)
        fields["discovered_at"] = iso(now)
        item_id = insert_item(conn, fields)
        stats["new_items"] += 1

        if not _within_days(fields["published_at"], recency_days, now):
            record_decision(
                conn,
                decision_type="stale",
                run_id=run_id,
                item_id=item_id,
                input_data={"url": fields["url"], "published_at": fields["published_at"]},
                output_data={"decision": "reject", "reason": "stale"},
            )
            stats["stale"] += 1
            # Still attach to a story so explain() can find it.
            story_id = insert_story(
                conn,
                primary_item_id=item_id,
                authority_score=authority_from_source(source.authority),
            )
            link_item(conn, story_id, item_id, "primary")
            conn.execute(
                """
                UPDATE stories
                SET decision = 'reject', decision_reason = 'stale', updated_at = ?
                WHERE id = ?
                """,
                (iso(now), story_id),
            )
            continue

        match = find_duplicate_story(
            conn,
            canonical_url=fields["canonical_url"],
            content_hash=fields["content_hash"],
            title=fields["title"],
        )
        if match:
            story_id, how = match
            primary_row = conn.execute(
                "SELECT source_id FROM items WHERE id = (SELECT primary_item_id FROM stories WHERE id = ?)",
                (story_id,),
            ).fetchone()
            if primary_row and primary_row["source_id"] != raw.source_id:
                relationship = "corroboration"
            else:
                relationship = "duplicate"
            link_item(conn, story_id, item_id, relationship)
            record_decision(
                conn,
                decision_type="dedupe",
                run_id=run_id,
                story_id=story_id,
                item_id=item_id,
                input_data={"url": fields["url"], "title": fields["title"]},
                output_data={"decision": "attach", "reason": how, "duplicate_of": story_id},
            )
            stats["duplicates"] += 1
            continue

        story_id = insert_story(
            conn,
            primary_item_id=item_id,
            authority_score=authority_from_source(source.authority),
        )
        link_item(conn, story_id, item_id, "primary")
        stats["stories_created"] += 1
    return stats


def run_pipeline(
    *,
    push: bool = False,
    settings: Settings | None = None,
    classifier: Classifier | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    scoring = load_scoring(settings)
    sources = [s for s in load_sources(settings) if s.enabled]
    token = github_token(settings)
    now = datetime.now(timezone.utc)
    recency_days = int((scoring.get("classify") or {}).get("recency_days", 14))
    max_classify = min(
        settings.hai_max_classify_per_run,
        int((scoring.get("classify") or {}).get("max_per_run", 40)),
    )
    digest_date = date or today_in_tz(settings.hai_timezone)
    totals: Counter[str] = Counter()
    source_errors: list[str] = []

    with session(settings) as conn:
        run_id = start_run(conn, "pipeline")
        try:
            for source in sources:
                stats = ingest_source(
                    conn,
                    source,
                    run_id=run_id,
                    token=token,
                    recency_days=recency_days,
                    now=now,
                )
                totals.update(stats)
                if stats.get("source_errors"):
                    source_errors.append(source.id)

            classify_stats: Counter[str] = Counter()
            for story in pending_stories(
                conn, recency_days=recency_days, limit=max_classify, now=now
            ):
                result = classify_story(
                    conn,
                    story,
                    run_id=run_id,
                    settings=settings,
                    classifier=classifier,
                )
                classify_stats[result.get("status", "unknown")] += 1

            path, story_ids = write_digest(conn, digest_date=digest_date, settings=settings)
            kept = conn.execute(
                "SELECT COUNT(*) AS n FROM stories WHERE decision = 'keep'"
            ).fetchone()["n"]
            rejected = conn.execute(
                "SELECT COUNT(*) AS n FROM stories WHERE decision = 'reject'"
            ).fetchone()["n"]
            reject_reasons = {
                row["decision_reason"]: row["n"]
                for row in conn.execute(
                    """
                    SELECT COALESCE(decision_reason, 'unknown') AS decision_reason, COUNT(*) AS n
                    FROM stories
                    WHERE decision = 'reject'
                    GROUP BY decision_reason
                    """
                )
            }
            metrics = {
                "sources_polled": len(sources),
                "items_fetched": totals["fetched"],
                "new_items": totals["new_items"],
                "already_seen": totals["already_seen"],
                "duplicates": totals["duplicates"],
                "stale": totals["stale"],
                "stories_created": totals["stories_created"],
                "source_errors": totals["source_errors"],
                "failed_sources": source_errors,
                "classified": dict(classify_stats),
                "kept_total": kept,
                "rejected_total": rejected,
                "reject_reasons": reject_reasons,
                "digest_stories": len(story_ids),
                "digest_path": str(path),
                "digest_date": digest_date,
            }
            push_result = None
            if push:
                try:
                    push_result = push_digest(path, digest_date)
                    metrics["push"] = push_result
                except GitError as exc:
                    metrics["push_error"] = str(exc)
            finish_run(conn, run_id, status="ok", metrics=metrics)
            metrics["run_id"] = run_id
            metrics["push_result"] = push_result
            return metrics
        except Exception as exc:
            finish_run(conn, run_id, status="error", error=str(exc))
            raise


def format_run_summary(metrics: dict[str, Any]) -> str:
    reasons = metrics.get("reject_reasons") or {}
    reason_lines = "\n".join(
        f"  {name}: {count}" for name, count in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
    ) or "  (none)"
    classified = metrics.get("classified") or {}
    return f"""Discovery run {metrics.get("digest_date")}

Sources polled:    {metrics.get("sources_polled", 0)}
Items fetched:     {metrics.get("items_fetched", 0)}
New items:         {metrics.get("new_items", 0)}
Already seen:      {metrics.get("already_seen", 0)}
Duplicates:        {metrics.get("duplicates", 0)}
Stale:             {metrics.get("stale", 0)}
Stories created:   {metrics.get("stories_created", 0)}
Source errors:     {metrics.get("source_errors", 0)}
Failed sources:    {", ".join(metrics.get("failed_sources") or []) or "(none)"}

Classified this run:
  keep:    {classified.get("keep", 0)}
  reject:  {classified.get("rejected", 0) + classified.get("reject", 0)}
  error:   {classified.get("error", 0)}

Rejected (all time in DB):
{reason_lines}

Kept (all time):      {metrics.get("kept_total", 0)}
Digest stories:       {metrics.get("digest_stories", 0)}
Digest:               {metrics.get("digest_path")}
"""
