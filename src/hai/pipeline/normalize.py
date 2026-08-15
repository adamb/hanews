from __future__ import annotations

from html import unescape
from html.parser import HTMLParser

from hai.models import RawItem
from hai.urls import canonicalize_url, content_hash, normalize_text


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return unescape(" ".join(self._chunks))


def strip_html(value: str) -> str:
    parser = _HTMLText()
    try:
        parser.feed(value or "")
        parser.close()
    except Exception:
        return unescape(value or "")
    return parser.text()


def normalized_item_fields(item: RawItem) -> dict:
    text = normalize_text(strip_html(item.raw_text))
    canonical = canonicalize_url(item.url)
    return {
        "source_id": item.source_id,
        "source_item_id": item.source_item_id,
        "url": item.url,
        "canonical_url": canonical,
        "title": normalize_text(item.title)[:500],
        "author": item.author,
        "published_at": item.published_at.isoformat(timespec="seconds") if item.published_at else None,
        "raw_text": text[:20000],
        "raw_metadata_json": None,
        "content_hash": content_hash(title=item.title, text=text),
    }
