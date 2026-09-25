"""URL identity helpers shared by source registration and review screening."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """Normalize a URL for identity checks without changing its query string."""
    if not isinstance(url, str):
        raise TypeError("url must be a string")
    value = url.strip()
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValueError(f"invalid URL: {url!r}") from exc
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.query,
            "",
        )
    )
