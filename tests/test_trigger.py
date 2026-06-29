"""Tests for the HAAPI trigger platform."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.trigger import TriggerConfig

from custom_components.haapi import trigger as trig
from custom_components.haapi.const import (
    ATTR_BODY,
    ATTR_BODY_CHANGED,
    ATTR_ENDPOINT_ID,
    ATTR_ENDPOINT_NAME,
    ATTR_ENTRY_ID,
    ATTR_HEADERS,
    ATTR_OK,
    ATTR_PREVIOUS_STATUS,
    ATTR_STATUS,
    ATTR_STATUS_CHANGED,
    ATTR_TRUNCATED,
    EVENT_HAAPI_RESPONSE,
)


def _data(**over):
    """Build a well-formed haapi_response payload, overridable per-key."""
    base = {
        ATTR_ENTRY_ID: "entry-1",
        ATTR_ENDPOINT_ID: "ep-1",
        ATTR_ENDPOINT_NAME: "Test Endpoint",
        ATTR_STATUS: 200,
        ATTR_OK: True,
        ATTR_BODY: "x",
        ATTR_HEADERS: {},
        ATTR_TRUNCATED: False,
        ATTR_STATUS_CHANGED: True,
        ATTR_BODY_CHANGED: True,
        ATTR_PREVIOUS_STATUS: None,
    }
    base.update(over)
    return base


def _make(cls, options=None, target=None, hass=None):
    return cls(hass, TriggerConfig(key=f"haapi.{cls.__name__}", target=target, options=options or {}))


async def test_get_triggers(hass: HomeAssistant) -> None:
    """All five triggers are exposed."""
    triggers = await trig.async_get_triggers(hass)
    assert set(triggers) == {
        "response_received",
        "call_succeeded",
        "call_failed",
        "response_changed",
        "status_changed",
    }


def test_event_matches_response_received() -> None:
    t = _make(trig.ResponseReceivedTrigger)
    assert t._event_matches(_data(status=200)) is True
    assert t._event_matches(_data(status=500)) is True
    # status filter
    t_filtered = _make(trig.ResponseReceivedTrigger, options={"status": 429})
    assert t_filtered._event_matches(_data(status=429)) is True
    assert t_filtered._event_matches(_data(status=200)) is False


def test_event_matches_succeeded_failed() -> None:
    ok = _make(trig.CallSucceededTrigger)
    assert ok._event_matches(_data(ok=True)) is True
    assert ok._event_matches(_data(ok=False)) is False

    fail = _make(trig.CallFailedTrigger)
    assert fail._event_matches(_data(status=0)) is True      # network error
    assert fail._event_matches(_data(status=404)) is True    # HTTP error
    assert fail._event_matches(_data(status=200)) is False


def test_event_matches_changed() -> None:
    body = _make(trig.ResponseChangedTrigger)
    assert body._event_matches(_data(body_changed=True)) is True
    assert body._event_matches(_data(body_changed=False)) is False

    status = _make(trig.StatusChangedTrigger)
    assert status._event_matches(_data(status_changed=True)) is True
    assert status._event_matches(_data(status_changed=False)) is False


async def test_validate_config(hass: HomeAssistant) -> None:
    cfg = await trig.ResponseReceivedTrigger.async_validate_config(
        hass, {"options": {"status": 429}}
    )
    assert cfg["options"]["status"] == 429
    cfg2 = await trig.CallFailedTrigger.async_validate_config(hass, {})
    assert cfg2["options"] == {}


async def test_attach_runner_fires_filters_and_unsubscribes(hass: HomeAssistant) -> None:
    """async_attach_runner fires on match, drops malformed events, unsubscribes."""
    calls: list[dict] = []

    def run_action(payload, description, context=None):
        calls.append(payload)

    t = _make(trig.ResponseReceivedTrigger, hass=hass)
    unsub = await t.async_attach_runner(run_action)

    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, _data())
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0]["platform"] == "haapi.ResponseReceivedTrigger"
    assert calls[0][ATTR_ENDPOINT_NAME] == "Test Endpoint"

    # Malformed event (missing required keys) is ignored, no KeyError.
    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, {ATTR_ENDPOINT_NAME: "x"})
    await hass.async_block_till_done()
    assert len(calls) == 1

    unsub()
    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, _data())
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_attach_runner_status_filter(hass: HomeAssistant) -> None:
    calls: list[dict] = []
    t = _make(trig.ResponseReceivedTrigger, options={"status": 429}, hass=hass)
    unsub = await t.async_attach_runner(lambda p, d, c=None: calls.append(p))

    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, _data(status=200))
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, _data(status=429))
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0][ATTR_STATUS] == 429
    unsub()
