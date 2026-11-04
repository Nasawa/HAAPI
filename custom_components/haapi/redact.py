"""Keep request secrets out of attributes and logs.

An endpoint URL can carry an API key in its query, credentials in its userinfo,
or a token in its path, so nothing user-visible should show the rendered URL.
Exception text is never shown either: aiohttp errors embed URLs (including
redirect targets) in forms that can't be reliably scrubbed.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit, urlunsplit

import aiohttp


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


def describe_error(err: BaseException) -> str:
    """Describe a request failure from its type and URL-free fields only."""
    name = type(err).__name__
    if isinstance(err, (asyncio.TimeoutError, TimeoutError)):
        detail = "timed out"
    elif isinstance(err, aiohttp.TooManyRedirects):
        detail = "too many redirects"
    elif isinstance(err, aiohttp.ClientResponseError):
        detail = f"HTTP {err.status}"
    elif isinstance(err, aiohttp.InvalidURL):
        detail = "invalid URL"
    elif isinstance(err, aiohttp.ClientSSLError):
        detail = "TLS/SSL error"
    elif isinstance(err, aiohttp.ClientConnectorError):
        reason = getattr(err.os_error, "strerror", None)
        detail = f"cannot connect ({reason})" if reason else "cannot connect"
    elif isinstance(err, aiohttp.ServerDisconnectedError):
        detail = "server disconnected"
    elif isinstance(err, aiohttp.ClientPayloadError):
        detail = "response payload error"
    else:
        detail = "request failed"
    return f"{name}: {detail}"
