from __future__ import annotations

from hai.discovery.github import GitHubReleaseDiscoverer
from hai.discovery.rss import RssDiscoverer
from hai.models import RawItem, Source


class UnknownSourceType(ValueError):
    pass


def discover_source(source: Source, *, github_token: str = "") -> list[RawItem]:
    if source.type == "rss":
        return RssDiscoverer(source).fetch()
    if source.type == "github_releases":
        return GitHubReleaseDiscoverer(source, token=github_token).fetch()
    raise UnknownSourceType(f"Unsupported source type: {source.type}")
