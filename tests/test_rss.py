from pathlib import Path

import respx
from httpx import Response

from hai.discovery.rss import RssDiscoverer
from hai.models import Source

FIXTURE = Path(__file__).parent / "fixtures" / "ha_atom.xml"


@respx.mock
def test_rss_discoverer_parses_atom() -> None:
    respx.get("https://example.test/atom.xml").mock(
        return_value=Response(200, content=FIXTURE.read_bytes())
    )
    source = Source(
        id="ha_blog",
        name="HA Blog",
        type="rss",
        url="https://example.test/atom.xml",
        authority=1.0,
    )
    items = RssDiscoverer(source).fetch()
    assert len(items) == 2
    assert items[0].title.startswith("2026.8")
    assert items[0].url.startswith("https://www.home-assistant.io/blog/2026/08/05/")
    assert "Matter" in items[0].raw_text
    assert items[0].published_at is not None
