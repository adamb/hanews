from hai.urls import canonicalize_url, content_hash, normalize_title


def test_canonical_url_strips_tracking_and_fragment() -> None:
    url = "HTTPS://www.Example.com:443/blog/post/?utm_source=rss&b=2&a=1#section"
    assert canonicalize_url(url) == "https://www.example.com/blog/post?a=1&b=2"


def test_canonical_url_keeps_nondefault_port() -> None:
    assert canonicalize_url("http://example.com:8080/x/") == "http://example.com:8080/x"


def test_normalize_title_ignores_punctuation() -> None:
    assert normalize_title("Home Assistant 2026.8: Approachable!") == (
        normalize_title("home assistant 2026 8 approachable")
    )


def test_content_hash_stable_and_case_insensitive() -> None:
    a = content_hash(title="Hello", text="Matter  over  Thread")
    b = content_hash(title="Hello", text="matter over thread")
    assert a == b
    assert len(a) == 64
