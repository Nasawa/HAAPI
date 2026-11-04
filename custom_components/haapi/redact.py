"""Keep request secrets out of attributes and logs.

An endpoint URL can carry an API key in its query, credentials in its userinfo,
or a token in its path, so nothing user-visible should show the rendered URL.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from yarl import URL

# Any http(s) URL left in free text: userinfo and query/fragment are dropped.
_URL_IN_TEXT = re.compile(r"(https?://)(?:[^\s'\"<>/@]*@)?([^\s'\"<>?#]*)(?:[?#][^\s'\"<>]*)?")


def redact_url(url: str) -> str:
    """Return the URL without user:password or query string (secrets often live there)."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return ""
    if ":" in host:
        host = f"[{host}]"
    if port:
        host = f"{host}:{port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def _spellings(url: str) -> set[str]:
    """The ways an HTTP client may print ``url``: as written, re-encoded, without credentials."""
    spellings = {url}
    try:
        parsed = URL(url)
        spellings.add(str(parsed))
        # aiohttp moves user:password into its auth settings and drops the fragment.
        bare = parsed.with_user(None) if parsed.is_absolute() else parsed
        spellings.update({str(bare), str(parsed.with_fragment(None)),
                          str(bare.with_fragment(None))})
    except (ValueError, TypeError):
        pass
    return spellings


def scrub_url(text: str, url: str, replacement: str) -> str:
    """Remove ``url`` and any other URL's secrets from ``text`` (e.g. an exception message).

    Known spellings of the request URL become ``replacement``. Any other URL
    still in the text (after a redirect, say) keeps only scheme, host and path.
    """
    for spelling in sorted(_spellings(url), key=len, reverse=True):
        if spelling:
            text = text.replace(spelling, replacement)
    return _URL_IN_TEXT.sub(r"\1\2", text)
