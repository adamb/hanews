from __future__ import annotations

import json
from datetime import datetime, timezone

from hai.http import fetch_bytes
from hai.models import RawItem, Source

GITHUB_API = "https://api.github.com"


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


class GitHubReleaseDiscoverer:
    def __init__(self, source: Source, *, token: str = "", per_page: int = 15) -> None:
        self.source = source
        self.token = token
        self.per_page = per_page

    def fetch(self) -> list[RawItem]:
        if not self.source.repo:
            raise ValueError(f"Source {self.source.id} is missing repo")
        url = f"{GITHUB_API}/repos/{self.source.repo}/releases?per_page={self.per_page}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = json.loads(fetch_bytes(url, headers=headers).decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Unexpected GitHub response for {self.source.repo}")

        items: list[RawItem] = []
        for release in payload:
            if release.get("draft"):
                continue
            html_url = release.get("html_url") or ""
            title = (release.get("name") or release.get("tag_name") or "").strip()
            if not html_url or not title:
                continue
            body = (release.get("body") or "")[:8000]
            items.append(
                RawItem(
                    source_id=self.source.id,
                    source_item_id=str(release.get("id") or html_url),
                    url=html_url,
                    title=title,
                    author=(release.get("author") or {}).get("login"),
                    published_at=_parse_dt(release.get("published_at") or release.get("created_at")),
                    raw_text=body,
                    raw_metadata={
                        "tag_name": release.get("tag_name"),
                        "prerelease": bool(release.get("prerelease")),
                        "repo": self.source.repo,
                    },
                )
            )
        return items
