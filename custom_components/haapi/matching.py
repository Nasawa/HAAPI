"""Shared body-matching helpers for HAAPI triggers and conditions.

A lightweight dotted-path resolver over a JSON body (no JSONPath dependency)
plus small helpers for regex validation and JSON-spelling comparisons.
"""

from __future__ import annotations

import json
import re
from typing import Any

import voluptuous as vol

# Sentinel for "path not resolvable" (distinct from a real None value).
UNSET = object()


def resolve_path(body: str | None, path: str) -> Any:
    """Resolve a dotted path (e.g. ``state`` or ``ams.0.humidity``) in a JSON body.

    Returns the value at the path, or ``UNSET`` if the body is not JSON or the
    path does not resolve. List indices are non-negative integers in the path.
    """
    if body is None:
        return UNSET
    try:
        current = json.loads(body)
    except (ValueError, TypeError):
        return UNSET
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return UNSET
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return UNSET
            # Non-negative indices only (JSON-pointer style); reject negatives.
            if not 0 <= index < len(current):
                return UNSET
            current = current[index]
        else:
            return UNSET
    return current


def value_text(value: Any) -> str:
    """Render a resolved value for comparison.

    Strings are returned raw; everything else uses its JSON spelling so
    booleans/null/numbers match what users see in the body (true/false/null).
    """
    return value if isinstance(value, str) else json.dumps(value)


def valid_regex(value: str) -> str:
    """Validate that a string compiles as a regex (voluptuous validator)."""
    try:
        re.compile(value)
    except re.error as err:
        raise vol.Invalid(f"Invalid regular expression: {err}") from err
    return value
