"""SQLite persistence. Database file lives on the backup disk."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from hai.config import Settings, get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    published_at TEXT,
    discovered_at TEXT NOT NULL,
    raw_text TEXT,
    raw_metadata_json TEXT,
    content_hash TEXT NOT NULL,
    UNIQUE(source_id, source_item_id)
);

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY,
    primary_item_id INTEGER REFERENCES items(id),
    topic TEXT,
    summary TEXT,
    relevance_score REAL,
    novelty_score REAL,
    importance_score REAL,
    authority_score REAL,
    personal_interest_score REAL,
    overall_score REAL,
    decision TEXT,
    decision_reason TEXT,
    why_it_matters TEXT,
    why_you_care TEXT,
    claims_json TEXT,
    topics_json TEXT,
    digest_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS story_items (
    story_id INTEGER NOT NULL REFERENCES stories(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    relationship TEXT NOT NULL,
    PRIMARY KEY (story_id, item_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    job_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    metrics_json TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY,
    story_id INTEGER,
    item_id INTEGER,
    run_id INTEGER,
    decision_type TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    model TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY,
    digest_date TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_canonical ON items(canonical_url);
CREATE INDEX IF NOT EXISTS idx_items_hash ON items(content_hash);
CREATE INDEX IF NOT EXISTS idx_items_title ON items(title);
CREATE INDEX IF NOT EXISTS idx_stories_decision ON stories(decision);
CREATE INDEX IF NOT EXISTS idx_stories_digest ON stories(digest_date);
CREATE INDEX IF NOT EXISTS idx_story_items_item ON story_items(item_id);
"""


def iso(dt: datetime | None = None) -> str:
    value = dt or datetime.now().astimezone()
    return value.isoformat(timespec="seconds")


def connect(settings: Settings | None = None) -> sqlite3.Connection:
    settings = settings or get_settings()
    path = settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def session(settings: Settings | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(settings)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dump_json(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def load_json(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)


def get_item_by_source_key(
    conn: sqlite3.Connection, source_id: str, source_item_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM items WHERE source_id = ? AND source_item_id = ?",
        (source_id, source_item_id),
    ).fetchone()


def insert_item(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO items (
            source_id, source_item_id, url, canonical_url, title, author,
            published_at, discovered_at, raw_text, raw_metadata_json, content_hash
        ) VALUES (
            :source_id, :source_item_id, :url, :canonical_url, :title, :author,
            :published_at, :discovered_at, :raw_text, :raw_metadata_json, :content_hash
        )
        """,
        payload,
    )
    return int(cur.lastrowid)


def insert_story(
    conn: sqlite3.Connection,
    *,
    primary_item_id: int,
    authority_score: float,
    created_at: str | None = None,
) -> int:
    now = created_at or iso()
    cur = conn.execute(
        """
        INSERT INTO stories (
            primary_item_id, authority_score, created_at, updated_at
        ) VALUES (?, ?, ?, ?)
        """,
        (primary_item_id, authority_score, now, now),
    )
    return int(cur.lastrowid)


def link_item(
    conn: sqlite3.Connection, story_id: int, item_id: int, relationship: str
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO story_items (story_id, item_id, relationship)
        VALUES (?, ?, ?)
        """,
        (story_id, item_id, relationship),
    )


def story_for_item(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT s.* FROM stories s
        JOIN story_items si ON si.story_id = s.id
        WHERE si.item_id = ?
        """,
        (item_id,),
    ).fetchone()


def find_story_by_canonical(conn: sqlite3.Connection, canonical_url: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT s.* FROM stories s
        JOIN story_items si ON si.story_id = s.id
        JOIN items i ON i.id = si.item_id
        WHERE i.canonical_url = ?
        ORDER BY s.id ASC
        LIMIT 1
        """,
        (canonical_url,),
    ).fetchone()


def find_story_by_hash(conn: sqlite3.Connection, content_hash: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT s.* FROM stories s
        JOIN story_items si ON si.story_id = s.id
        JOIN items i ON i.id = si.item_id
        WHERE i.content_hash = ?
        ORDER BY s.id ASC
        LIMIT 1
        """,
        (content_hash,),
    ).fetchone()


def recent_story_titles(
    conn: sqlite3.Connection, limit: int = 400
) -> list[tuple[int, str]]:
    rows = conn.execute(
        """
        SELECT s.id, i.title
        FROM stories s
        JOIN items i ON i.id = s.primary_item_id
        ORDER BY s.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [(int(row["id"]), row["title"]) for row in rows]


def start_run(conn: sqlite3.Connection, job_name: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO runs (job_name, started_at, status)
        VALUES (?, ?, 'running')
        """,
        (job_name, iso()),
    )
    return int(cur.lastrowid)


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    status: str,
    metrics: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE runs
        SET finished_at = ?, status = ?, metrics_json = ?, error = ?
        WHERE id = ?
        """,
        (iso(), status, dump_json(metrics or {}), error, run_id),
    )


def record_decision(
    conn: sqlite3.Connection,
    *,
    decision_type: str,
    run_id: int | None = None,
    story_id: int | None = None,
    item_id: int | None = None,
    input_data: Any = None,
    output_data: Any = None,
    model: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO decisions (
            story_id, item_id, run_id, decision_type, input_json, output_json, model, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            story_id,
            item_id,
            run_id,
            decision_type,
            dump_json(input_data) if input_data is not None else None,
            dump_json(output_data) if output_data is not None else None,
            model,
            iso(),
        ),
    )
    return int(cur.lastrowid)


def update_story(conn: sqlite3.Connection, story_id: int, fields: dict[str, Any]) -> None:
    if not fields:
        return
    fields = {**fields, "updated_at": iso()}
    assignments = ", ".join(f"{key} = :{key}" for key in fields)
    fields["id"] = story_id
    conn.execute(f"UPDATE stories SET {assignments} WHERE id = :id", fields)


def story_items(conn: sqlite3.Connection, story_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT i.*, si.relationship
            FROM story_items si
            JOIN items i ON i.id = si.item_id
            WHERE si.story_id = ?
            ORDER BY i.published_at IS NULL, i.published_at DESC, i.id ASC
            """,
            (story_id,),
        )
    )


def get_story(conn: sqlite3.Connection, story_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()


def find_item_by_url(conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM items WHERE url = ? OR canonical_url = ? LIMIT 1",
        (url, url),
    ).fetchone()


def db_file(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.db_path
