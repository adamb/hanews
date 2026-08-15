from datetime import datetime, timezone
from pathlib import Path

import respx
from httpx import Response

from hai.llm.schemas import Classification
from hai.pipeline.run import format_run_summary, run_pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "ha_atom.xml"

NOISE_FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Noise</title>
<item>
  <title>Best phones of 2026</title>
  <link>https://example.test/phones</link>
  <guid>https://example.test/phones</guid>
  <pubDate>Sat, 15 Aug 2026 10:00:00 GMT</pubDate>
  <description>A roundup of flagship phones.</description>
</item>
</channel></rss>
"""

GITHUB_JSON = """
[
  {
    "id": 99,
    "html_url": "https://github.com/home-assistant/core/releases/tag/2026.8.0",
    "name": "2026.8.0",
    "tag_name": "2026.8.0",
    "body": "Home Assistant Core 2026.8.0",
    "draft": false,
    "prerelease": false,
    "published_at": "2026-08-06T00:00:00Z",
    "author": {"login": "balloob"}
  }
]
"""


def fake_classifier(**kwargs):
    title = kwargs["title"]
    if "phones" in title.lower():
        return Classification(
            topics=["industry"],
            relevance_score=10,
            novelty_score=10,
            importance_score=10,
            personal_interest_score=5,
            decision="reject",
            reason="consumer gadget recap",
            why_it_matters="Does not change the home-automation stack.",
            why_you_care="You do not need another phone review.",
            claims_to_verify=[],
            summary=title,
        )
    return Classification(
        topics=["home_assistant"],
        relevance_score=90,
        novelty_score=80,
        importance_score=80,
        personal_interest_score=90,
        decision="keep",
        reason="Official Home Assistant release.",
        why_it_matters="Core platform changes.",
        why_you_care="You run Home Assistant.",
        claims_to_verify=["release notes"],
        summary=title,
    )


@respx.mock
def test_pipeline_end_to_end(tmp_settings) -> None:
    respx.get("https://example.test/atom.xml").mock(
        return_value=Response(200, content=FIXTURE.read_bytes())
    )
    respx.get("https://example.test/noise.xml").mock(
        return_value=Response(200, content=NOISE_FEED.encode())
    )
    respx.get(url__regex=r"https://api.github.com/repos/home-assistant/core/releases.*").mock(
        return_value=Response(200, content=GITHUB_JSON.encode())
    )
    # A broken extra request should not appear; isolation is tested separately.
    metrics = run_pipeline(
        settings=tmp_settings,
        classifier=fake_classifier,
        date="2026-08-15",
    )
    assert metrics["new_items"] >= 3
    assert metrics["stories_created"] >= 2
    digest = Path(metrics["digest_path"]).read_text(encoding="utf-8")
    assert "2026.8" in digest
    assert "Best phones" not in digest
    assert "HOME AUTOMATION DAILY BRIEF" in digest
    summary = format_run_summary(metrics)
    assert "Sources polled" in summary


@respx.mock
def test_broken_source_does_not_abort(tmp_settings, monkeypatch) -> None:
    import hai.http as http_mod

    monkeypatch.setattr(http_mod.time, "sleep", lambda _s: None)
    respx.get("https://example.test/atom.xml").mock(return_value=Response(500))
    respx.get("https://example.test/noise.xml").mock(
        return_value=Response(200, content=NOISE_FEED.encode())
    )
    respx.get(url__regex=r"https://api.github.com/repos/home-assistant/core/releases.*").mock(
        return_value=Response(200, content=GITHUB_JSON.encode())
    )
    metrics = run_pipeline(
        settings=tmp_settings,
        classifier=fake_classifier,
        date="2026-08-15",
    )
    assert metrics["source_errors"] >= 1
    assert "ha_blog" in metrics["failed_sources"]
    assert metrics["new_items"] >= 1
