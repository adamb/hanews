from datetime import datetime, timezone

from hai.db import insert_item, insert_story, iso, link_item
from hai.pipeline.dedupe import find_duplicate_story, title_similarity
from hai.urls import canonicalize_url, content_hash


def test_title_similarity_near_duplicates() -> None:
    assert title_similarity(
        "Home Assistant 2026.8: Approachable by design",
        "Home Assistant 2026.8 — Approachable by design",
    ) >= 0.88


def test_find_duplicate_by_url_and_hash(db) -> None:
    now = iso(datetime.now(timezone.utc))
    url = "https://example.com/story"
    text = "A Matter over Thread presence sensor"
    item_id = insert_item(
        db,
        {
            "source_id": "ha_blog",
            "source_item_id": "1",
            "url": url,
            "canonical_url": canonicalize_url(url + "?utm_source=x"),
            "title": "New presence sensor",
            "author": None,
            "published_at": now,
            "discovered_at": now,
            "raw_text": text,
            "raw_metadata_json": "{}",
            "content_hash": content_hash(title="New presence sensor", text=text),
        },
    )
    story_id = insert_story(db, primary_item_id=item_id, authority_score=100)
    link_item(db, story_id, item_id, "primary")

    by_url = find_duplicate_story(
        db,
        canonical_url=canonicalize_url(url),
        content_hash="nope",
        title="unrelated",
    )
    assert by_url == (story_id, "canonical_url")

    by_hash = find_duplicate_story(
        db,
        canonical_url="https://other.example/x",
        content_hash=content_hash(title="New presence sensor", text=text),
        title="unrelated",
    )
    assert by_hash == (story_id, "content_hash")

    by_title = find_duplicate_story(
        db,
        canonical_url="https://other.example/y",
        content_hash="abc",
        title="New presence sensor!",
    )
    assert by_title == (story_id, "title_similarity")
