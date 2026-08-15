"""HTTP client with timeout, retries, and source isolation helpers."""

from __future__ import annotations

import time
from collections.abc import Mapping

import httpx

DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 3
USER_AGENT = "hai-news/0.1 (+https://github.com/adamb/hanews)"


class FetchError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def fetch_text(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> str:
    return fetch_bytes(url, headers=headers, timeout=timeout, retries=retries).decode(
        "utf-8",
        errors="replace",
    )


def fetch_bytes(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> bytes:
    merged = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged.update(dict(headers))
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers=merged)
            if response.status_code >= 500 or response.status_code == 429:
                last_error = FetchError(
                    f"{url} returned {response.status_code}",
                    status_code=response.status_code,
                )
                time.sleep(1.5 * (attempt + 1))
                continue
            if response.status_code >= 400:
                raise FetchError(
                    f"{url} returned {response.status_code}",
                    status_code=response.status_code,
                )
            return response.content
        except httpx.HTTPError as exc:
            last_error = FetchError(f"{url} failed: {exc}")
            time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error
