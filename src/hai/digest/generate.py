from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from hai.config import Settings, get_settings, load_scoring
from hai.db import dump_json, iso, load_json, story_items, update_story


def today_in_tz(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).date().isoformat()


def select_digest_stories(
    conn: sqlite3.Connection,
    *,
    digest_date: str,
    settings: Settings | None = None,
) -> list[sqlite3.Row]:
    settings = settings or get_settings()
    scoring = load_scoring(settings)
    digest_cfg = scoring.get("digest") or {}
    max_stories = int(digest_cfg.get("max_stories", 8))
    min_score = float(digest_cfg.get("min_overall_score", 55))
    recency_days = int(digest_cfg.get("recency_days", 7))
    cutoff = (
        datetime.fromisoformat(digest_date) - timedelta(days=recency_days)
    ).date().isoformat()
    return list(
        conn.execute(
            """
            SELECT s.*, i.title AS title, i.url AS url, i.source_id AS source_id,
                   i.published_at AS published_at, i.canonical_url AS canonical_url
            FROM stories s
            JOIN items i ON i.id = s.primary_item_id
            WHERE s.decision = 'keep'
              AND s.overall_score >= ?
              AND (s.digest_date IS NULL OR s.digest_date = ?)
              AND (
                    i.published_at IS NULL
                    OR substr(i.published_at, 1, 10) >= ?
                    OR substr(s.created_at, 1, 10) >= ?
              )
            ORDER BY s.overall_score DESC, i.published_at DESC
            LIMIT ?
            """,
            (min_score, digest_date, cutoff, cutoff, max_stories),
        )
    )


def _topic_label(row: sqlite3.Row) -> str:
    topics = load_json(row["topics_json"], []) or []
    if topics:
        return ", ".join(t.replace("_", " ").title() for t in topics)
    if row["topic"]:
        return str(row["topic"]).replace("_", " ").title()
    return "General"


def _sources_block(conn: sqlite3.Connection, story_id: int) -> str:
    lines: list[str] = []
    for item in story_items(conn, story_id):
        rel = item["relationship"]
        mark = "primary" if rel == "primary" else rel
        lines.append(f"   - [{item['title']}]({item['url']}) ({item['source_id']}, {mark})")
    return "\n".join(lines) if lines else "   - (no sources)"


def render_digest(
    conn: sqlite3.Connection,
    stories: list[sqlite3.Row],
    *,
    digest_date: str,
) -> str:
    lines = [
        f"# HOME AUTOMATION DAILY BRIEF",
        f"",
        f"Date: {digest_date}",
        f"",
    ]
    if not stories:
        lines.append("No stories crossed the threshold today.")
        lines.append("")
        return "\n".join(lines)

    for index, story in enumerate(stories, start=1):
        score = story["overall_score"] if story["overall_score"] is not None else 0
        lines.extend(
            [
                f"{index}. {story['title']}",
                f"   Score: {score:.0f}",
                f"   Topics: {_topic_label(story)}",
                f"",
                f"   What happened:",
                f"   {story['summary'] or story['title']}",
                f"",
                f"   Why it matters:",
                f"   {story['why_it_matters'] or '—'}",
                f"",
                f"   Why you care:",
                f"   {story['why_you_care'] or '—'}",
                f"",
                f"   Sources:",
                _sources_block(conn, int(story["id"])),
                f"",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_digest(
    conn: sqlite3.Connection,
    *,
    digest_date: str | None = None,
    settings: Settings | None = None,
) -> tuple[Path, list[int]]:
    settings = settings or get_settings()
    digest_date = digest_date or today_in_tz(settings.hai_timezone)
    stories = select_digest_stories(conn, digest_date=digest_date, settings=settings)
    body = render_digest(conn, stories, digest_date=digest_date)
    path = settings.digest_dir / f"{digest_date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")

    story_ids = [int(row["id"]) for row in stories]
    for story_id in story_ids:
        update_story(conn, story_id, {"digest_date": digest_date})
    conn.execute(
        """
        INSERT INTO digests (digest_date, path, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(digest_date) DO UPDATE SET path = excluded.path
        """,
        (digest_date, str(path), iso()),
    )
    return path, story_ids
