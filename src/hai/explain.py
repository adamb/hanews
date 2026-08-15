from __future__ import annotations

import sqlite3

from hai.db import find_item_by_url, get_story, load_json, story_for_item, story_items
from hai.urls import canonicalize_url


def resolve_story(conn: sqlite3.Connection, ref: str) -> sqlite3.Row | None:
    if ref.isdigit():
        story = get_story(conn, int(ref))
        if story:
            return story
        item = conn.execute("SELECT * FROM items WHERE id = ?", (int(ref),)).fetchone()
        if item:
            return story_for_item(conn, int(item["id"]))
    item = find_item_by_url(conn, ref) or find_item_by_url(conn, canonicalize_url(ref))
    if item:
        return story_for_item(conn, int(item["id"]))
    return None


def format_explanation(conn: sqlite3.Connection, story: sqlite3.Row) -> str:
    items = story_items(conn, int(story["id"]))
    decisions = list(
        conn.execute(
            """
            SELECT * FROM decisions
            WHERE story_id = ? OR item_id IN (
                SELECT item_id FROM story_items WHERE story_id = ?
            )
            ORDER BY id ASC
            """,
            (int(story["id"]), int(story["id"])),
        )
    )
    topics = load_json(story["topics_json"], []) or []
    lines = [
        f"Story {story['id']}",
        f"Decision: {story['decision'] or '(pending)'}",
        f"Reason: {story['decision_reason'] or '—'}",
        f"Overall: {story['overall_score']}",
        f"Relevance: {story['relevance_score']}  Novelty: {story['novelty_score']}  "
        f"Importance: {story['importance_score']}  Authority: {story['authority_score']}  "
        f"Personal: {story['personal_interest_score']}",
        f"Topics: {', '.join(topics) or story['topic'] or '—'}",
        f"Digest: {story['digest_date'] or '(not included)'}",
        f"Summary: {story['summary'] or '—'}",
        "",
        "Items:",
    ]
    for item in items:
        lines.append(
            f"  [{item['relationship']}] {item['source_id']} {item['title']}"
        )
        lines.append(f"      {item['url']}")
        lines.append(
            f"      published={item['published_at'] or '—'} hash={item['content_hash'][:12]}"
        )
    lines.append("")
    lines.append("Decisions:")
    if not decisions:
        lines.append("  (none recorded)")
    for row in decisions:
        lines.append(
            f"  #{row['id']} {row['created_at']} {row['decision_type']} model={row['model'] or '-'}"
        )
        if row["output_json"]:
            lines.append(f"      {row['output_json'][:500]}")
    return "\n".join(lines) + "\n"
