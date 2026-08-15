from datetime import datetime, timezone

from hai.db import insert_item, insert_story, iso, link_item, update_story
from hai.digest.generate import render_digest, write_digest


def _keep_story(db, *, title: str, url: str, score: float, source_id: str = "ha_blog") -> int:
    now = iso(datetime.now(timezone.utc))
    item_id = insert_item(
        db,
        {
            "source_id": source_id,
            "source_item_id": url,
            "url": url,
            "canonical_url": url,
            "title": title,
            "author": None,
            "published_at": now,
            "discovered_at": now,
            "raw_text": title,
            "raw_metadata_json": "{}",
            "content_hash": title,
        },
    )
    story_id = insert_story(db, primary_item_id=item_id, authority_score=100)
    link_item(db, story_id, item_id, "primary")
    update_story(
        db,
        story_id,
        {
            "decision": "keep",
            "decision_reason": "test",
            "overall_score": score,
            "summary": f"{title} happened.",
            "why_it_matters": "It matters.",
            "why_you_care": "You run HA.",
            "topics_json": '["home_assistant"]',
        },
    )
    return story_id


def test_render_and_write_digest(db, tmp_settings) -> None:
    _keep_story(db, title="HA 2026.8", url="https://example.test/a", score=90)
    _keep_story(db, title="Low score", url="https://example.test/b", score=10)
    path, ids = write_digest(db, digest_date="2026-08-15", settings=tmp_settings)
    text = path.read_text(encoding="utf-8")
    assert "HOME AUTOMATION DAILY BRIEF" in text
    assert "HA 2026.8" in text
    assert "Low score" not in text
    assert "Why it matters:" in text
    assert ids
    story = db.execute("SELECT digest_date FROM stories WHERE id = ?", (ids[0],)).fetchone()
    assert story["digest_date"] == "2026-08-15"


def test_empty_digest_still_writes(db, tmp_settings) -> None:
    path, ids = write_digest(db, digest_date="2026-08-15", settings=tmp_settings)
    assert path.exists()
    assert ids == []
    assert "No stories crossed the threshold" in path.read_text(encoding="utf-8")
    assert render_digest(db, [], digest_date="2026-08-15")
