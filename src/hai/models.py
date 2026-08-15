"""In-memory records used by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Source:
    id: str
    name: str
    type: str
    authority: float
    categories: list[str] = field(default_factory=list)
    url: str | None = None
    repo: str | None = None
    poll_interval: str | None = None
    enabled: bool = True


@dataclass(slots=True)
class RawItem:
    source_id: str
    source_item_id: str
    url: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    raw_text: str = ""
    raw_metadata: dict[str, Any] = field(default_factory=dict)
