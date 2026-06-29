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
        return session

    if not responses:
        raise ValueError("make_session requires at least one response or raise_exc=")

    if len(responses) == 1:
        # Single response: request() can be called any number of times.
        session.request = MagicMock(return_value=_request_cm(responses[0]))
        return session

    # Multiple responses: return each in turn, with a clear error if the code
    # under test calls request() more times than responses were provided
    # (instead of a confusing StopIteration).
    cms = [_request_cm(r) for r in responses]

    def _next_cm(*_args, **_kwargs):
        if not cms:
            raise AssertionError(
                f"make_session: request() called more than the {len(responses)} "
                "responses provided"
            )
        return cms.pop(0)

    session.request = MagicMock(side_effect=_next_cm)
    return session


def mock_client_session(status, body, headers=None):
    """Convenience: a session whose single response has the given status/body."""
    return make_session(make_response(status, body, headers))
