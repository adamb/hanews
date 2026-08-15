from datetime import datetime, timezone

import pytest

from hai.db import get_item_by_source_key, insert_item, iso, record_decision, start_run


def test_item_unique_per_source(db) -> None:
    now = iso(datetime.now(timezone.utc))
    payload = {
        "source_id": "ha_blog",
        "source_item_id": "abc",
        "url": "https://example.com/a",
        "canonical_url": "https://example.com/a",
        "title": "A",
        "author": None,
        "published_at": now,
        "discovered_at": now,
        "raw_text": "hello",
        "raw_metadata_json": "{}",
        "content_hash": "x" * 64,
    }
    insert_item(db, payload)
    assert get_item_by_source_key(db, "ha_blog", "abc") is not None
    with pytest.raises(Exception):
        insert_item(db, payload)


def test_run_and_decision_roundtrip(db) -> None:
    run_id = start_run(db, "test")
    decision_id = record_decision(
        db,
        decision_type="reject",
        run_id=run_id,
        input_data={"url": "https://example.com"},
        output_data={"reason": "duplicate"},
    )
    row = db.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
    assert row["decision_type"] == "reject"
    assert "duplicate" in row["output_json"]
