from __future__ import annotations

import sqlite3
from difflib import SequenceMatcher

from hai.db import (
    find_story_by_canonical,
    find_story_by_hash,
    recent_story_titles,
)
from hai.urls import normalize_title

DEFAULT_TITLE_THRESHOLD = 0.88


def title_similarity(left: str, right: str) -> float:
    a = normalize_title(left)
    b = normalize_title(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def find_duplicate_story(
    conn: sqlite3.Connection,
    *,
    canonical_url: str,
    content_hash: str,
    title: str,
    title_threshold: float = DEFAULT_TITLE_THRESHOLD,
) -> tuple[int, str] | None:
    by_url = find_story_by_canonical(conn, canonical_url)
    if by_url:
        return int(by_url["id"]), "canonical_url"
    by_hash = find_story_by_hash(conn, content_hash)
    if by_hash:
        return int(by_hash["id"]), "content_hash"
    best_id = None
    best_score = title_threshold
    for story_id, existing_title in recent_story_titles(conn):
        score = title_similarity(title, existing_title)
        if score >= best_score:
            best_id = story_id
            best_score = score
    if best_id is not None:
        return best_id, "title_similarity"
    return None
