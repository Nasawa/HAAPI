"""Keep request secrets out of attributes and logs.

An endpoint URL can carry an API key in its query, credentials in its userinfo,
or a token in its path, so nothing user-visible should show the rendered URL.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from yarl import URL


def redact_url(url: str) -> str:
    """Return the URL without user:password or query string (secrets often live there)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def scrub_url(text: str, url: str, replacement: str) -> str:
    """Replace every spelling of ``url`` in ``text`` (e.g. an exception message).

    aiohttp formats URLs through yarl, which may re-encode them, so both the
    rendered string and yarl's spelling are replaced.
    """
    spellings = {url}
    try:
        spellings.add(str(URL(url)))
    except (ValueError, TypeError):
        pass
    for spelling in sorted(spellings, key=len, reverse=True):
        if spelling:
            text = text.replace(spelling, replacement)
    return text
