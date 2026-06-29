"""Shared test helpers for HAAPI.

The integration calls ``async with session.request(...) as response:``. A bare
``AsyncMock`` whose ``request`` returns the response does NOT form a valid async
context manager (the call returns a coroutine, not a CM), so the request path
raises and the caller records a status 0. These helpers build a session mock
whose ``request`` returns a proper async context manager.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


def make_response(status, body, headers=None):
    """Build a mock aiohttp response with the given status/body/headers."""
    response = AsyncMock()
    response.status = status
    response.text = AsyncMock(return_value=body)
    response.headers = headers or {}
    return response


def _request_cm(response):
    """Wrap a response in an async context manager (what request() returns)."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def make_session(*responses, raise_exc=None):
    """Build a mock aiohttp.ClientSession usable as an async context manager.

    - ``make_session(resp)`` -> request() always returns ``resp``.
    - ``make_session(r1, r2, r3)`` -> request() returns each in turn (retries).
    - ``make_session(raise_exc=exc)`` -> request() raises ``exc`` on every call.
    """
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    if raise_exc is not None:
        session.request = MagicMock(side_effect=raise_exc)
    elif len(responses) == 1:
        session.request = MagicMock(return_value=_request_cm(responses[0]))
    else:
        session.request = MagicMock(side_effect=[_request_cm(r) for r in responses])
    return session


def mock_client_session(status, body, headers=None):
    """Convenience: a session whose single response has the given status/body."""
    return make_session(make_response(status, body, headers))
