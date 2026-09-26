"""URL identity helpers shared by source registration and review screening."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def _normalize_netloc(netloc: str) -> str:
    userinfo, separator, host_port = netloc.rpartition("@")
    prefix = f"{userinfo}@" if separator else ""

    if host_port.startswith("["):
        closing_bracket = host_port.find("]")
        if closing_bracket < 0:
            return prefix + host_port
        host = host_port[1:closing_bracket]
        suffix = host_port[closing_bracket + 1 :]
        address, zone_separator, zone = host.partition("%")
        normalized_host = address.lower()
        if zone_separator:
            normalized_host += zone_separator + zone
        return f"{prefix}[{normalized_host}]{suffix}"

    host, port_separator, port = host_port.partition(":")
    return f"{prefix}{host.lower()}{port_separator}{port}"


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
            _normalize_netloc(parsed.netloc),
            parsed.path.rstrip("/"),
            parsed.query,
            "",
        )
    )
