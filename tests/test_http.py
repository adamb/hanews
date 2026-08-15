import respx
from httpx import Response

import hai.http as http_mod
from hai.http import FetchError, fetch_text


@respx.mock
def test_fetch_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(http_mod.time, "sleep", lambda _s: None)
    route = respx.get("https://example.test/feed")
    route.side_effect = [
        Response(500),
        Response(200, text="ok"),
    ]
    assert fetch_text("https://example.test/feed") == "ok"
    assert route.call_count == 2


@respx.mock
def test_fetch_does_not_retry_client_error(monkeypatch) -> None:
    monkeypatch.setattr(http_mod.time, "sleep", lambda _s: None)
    respx.get("https://example.test/missing").mock(return_value=Response(404))
    try:
        fetch_text("https://example.test/missing")
        raise AssertionError("expected FetchError")
    except FetchError as exc:
        assert exc.status_code == 404
