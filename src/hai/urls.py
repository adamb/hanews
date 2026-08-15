"""Deterministic URL and text normalization."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_cid",
    "utm_reader",
    "utm_name",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "ncid",
    "cmpid",
    "ocid",
    "spm",
    "ns_campaign",
    "ns_mchannel",
    "ns_source",
    "ns_linkname",
    "ns_fee",
    "_hsenc",
    "_hsmi",
    "mkt_tok",
    "vero_id",
    "wickedid",
    "yclid",
}

_TITLE_NOISE = re.compile(
    r"[\W_]+",
    flags=re.UNICODE,
)
_WHITESPACE = re.compile(r"\s+")


def canonicalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    scheme = (parts.scheme or "https").lower()
    host = (parts.hostname or "").lower()
    if not host:
        return raw

    port = parts.port
    if port and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query_pairs.sort(key=lambda kv: (kv[0].lower(), kv[1]))
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title(title: str) -> str:
    text = (title or "").casefold()
    text = _TITLE_NOISE.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def normalize_text(text: str) -> str:
    return _WHITESPACE.sub(" ", (text or "").strip())


def content_hash(*, title: str, text: str) -> str:
    payload = normalize_text(text) or title
    payload = _WHITESPACE.sub(" ", payload).strip().casefold()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
