from datetime import datetime, timezone

from hai.db import insert_item, insert_story, iso, link_item, record_decision, update_story
from hai.explain import format_explanation, resolve_story


def test_explain_by_url_and_id(db) -> None:
    now = iso(datetime.now(timezone.utc))
    url = "https://example.test/story"
    item_id = insert_item(
        db,
        {
            "source_id": "ha_blog",
            "source_item_id": "s1",
            "url": url,
            "canonical_url": url,
            "title": "Thread border router update",
            "author": None,
            "published_at": now,
            "discovered_at": now,
            "raw_text": "Matter over Thread",
            "raw_metadata_json": "{}",
            "content_hash": "abc",
        },
    )
    story_id = insert_story(db, primary_item_id=item_id, authority_score=90)
    link_item(db, story_id, item_id, "primary")
    update_story(
        db,
        story_id,
        {
            "decision": "keep",
            "decision_reason": "high signal",
            "overall_score": 88,
            "summary": "A Thread update.",
        },
    )
    record_decision(
        db,
        decision_type="classify",
        story_id=story_id,
        item_id=item_id,
        output_data={"decision": "keep"},
    )
    story = resolve_story(db, url)
    assert story is not None
    assert int(story["id"]) == story_id
    text = format_explanation(db, story)
    assert "Decision: keep" in text
    assert "high signal" in text
    assert resolve_story(db, str(story_id))["id"] == story_id
