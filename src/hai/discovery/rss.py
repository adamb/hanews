from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time

import feedparser

from hai.http import fetch_bytes
from hai.models import RawItem, Source


def _published(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed: struct_time | None = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            value = parsedate_to_datetime(raw)
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value
        except (TypeError, ValueError, OverflowError):
            continue
    return None


def _text(entry: feedparser.FeedParserDict) -> str:
    if entry.get("summary"):
        return str(entry.summary)
    details = entry.get("content") or []
    if details:
        first = details[0]
        if isinstance(first, dict):
            return str(first.get("value") or "")
        return str(first)
    return ""


class RssDiscoverer:
    def __init__(self, source: Source) -> None:
        self.source = source

    def fetch(self) -> list[RawItem]:
        if not self.source.url:
            raise ValueError(f"Source {self.source.id} is missing url")
        body = fetch_bytes(
            self.source.url,
            headers={"Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml"},
        )
        parsed = feedparser.parse(body)
        items: list[RawItem] = []
        for entry in parsed.entries:
            url = (
                entry.get("link")
                or (entry.get("id") if str(entry.get("id", "")).startswith("http") else "")
                or ""
            )
            title = (entry.get("title") or "").strip()
            if not url or not title:
                continue
            source_item_id = str(entry.get("id") or url)
            items.append(
                RawItem(
                    source_id=self.source.id,
                    source_item_id=source_item_id,
                    url=url,
                    title=title,
                    author=_author(entry),
                    published_at=_published(entry),
                    raw_text=_text(entry),
                    raw_metadata={
                        "feed_title": getattr(parsed.feed, "title", None),
                        "tags": [t.get("term") for t in entry.get("tags", []) if t.get("term")],
                    },
                )
            )
        return items


def _author(entry: feedparser.FeedParserDict) -> str | None:
    if entry.get("author"):
        return str(entry.author)
    authors = entry.get("authors") or []
    names = [a.get("name") for a in authors if isinstance(a, dict) and a.get("name")]
    return ", ".join(names) if names else None
