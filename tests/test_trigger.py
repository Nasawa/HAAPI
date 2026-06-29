"""Tests for the HAAPI trigger platform."""

import pytest
import voluptuous as vol
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
    ATTR_PREVIOUS_BODY,
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
        ATTR_PREVIOUS_BODY: None,
    }
    base.update(over)
    return base


def _make(cls, options=None, target=None, hass=None):
    return cls(hass, TriggerConfig(key=f"haapi.{cls.__name__}", target=target, options=options or {}))


async def test_get_triggers(hass: HomeAssistant) -> None:
    """All triggers are exposed."""
    triggers = await trig.async_get_triggers(hass)
    assert set(triggers) == {
        "response_received",
        "call_succeeded",
        "call_failed",
        "response_changed",
        "status_changed",
        "body_matches",
        "value_matches",
        "value_changed",
        "recovered",
        "went_down",
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


# ---------------------------------------------------------------------------
# Content / JSON-path / health-edge triggers (2.8.0)
# ---------------------------------------------------------------------------

_JSON_BODY = '{"state": "FINISH", "progress": 100.0, "ams": [{"humidity": 25}]}'


def test_resolve_path() -> None:
    assert trig._resolve_path(_JSON_BODY, "state") == "FINISH"
    assert trig._resolve_path(_JSON_BODY, "ams.0.humidity") == 25
    assert trig._resolve_path(_JSON_BODY, "ams.5.humidity") is trig._UNSET  # bad index
    assert trig._resolve_path(_JSON_BODY, "ams.-1.humidity") is trig._UNSET  # no negatives
    assert trig._resolve_path(_JSON_BODY, "missing") is trig._UNSET
    assert trig._resolve_path("not json", "state") is trig._UNSET
    assert trig._resolve_path(None, "state") is trig._UNSET


def test_value_matches_json_spelling() -> None:
    body = '{"connected": true, "progress": 100.0, "child": null}'
    # JSON booleans/numbers/null match their JSON spelling, not Python's.
    assert _make(
        trig.ValueMatchesTrigger, options={"path": "connected", "equals": "true"}
    )._event_matches(_data(body=body)) is True
    assert _make(
        trig.ValueMatchesTrigger, options={"path": "progress", "equals": "100.0"}
    )._event_matches(_data(body=body)) is True
    assert _make(
        trig.ValueMatchesTrigger, options={"path": "child", "equals": "null"}
    )._event_matches(_data(body=body)) is True
    # Python spelling does NOT match.
    assert _make(
        trig.ValueMatchesTrigger, options={"path": "connected", "equals": "True"}
    )._event_matches(_data(body=body)) is False


def test_body_matches() -> None:
    t = _make(trig.BodyMatchesTrigger, options={"pattern": r'"state":\s*"FINISH"'})
    assert t._event_matches(_data(body=_JSON_BODY)) is True
    assert t._event_matches(_data(body='{"state": "RUNNING"}')) is False
    assert t._event_matches(_data(body=None)) is False


def test_value_matches_equals_and_pattern() -> None:
    eq = _make(trig.ValueMatchesTrigger, options={"path": "state", "equals": "FINISH"})
    assert eq._event_matches(_data(body=_JSON_BODY)) is True
    assert eq._event_matches(_data(body='{"state": "RUNNING"}')) is False
    # missing path
    assert eq._event_matches(_data(body='{"x": 1}')) is False

    pat = _make(trig.ValueMatchesTrigger, options={"path": "state", "pattern": "^FIN"})
    assert pat._event_matches(_data(body=_JSON_BODY)) is True

    # neither equals nor pattern -> fires when path resolves
    exists = _make(trig.ValueMatchesTrigger, options={"path": "ams.0.humidity"})
    assert exists._event_matches(_data(body=_JSON_BODY)) is True
    assert exists._event_matches(_data(body='{"x": 1}')) is False


def test_value_changed() -> None:
    t = _make(trig.ValueChangedTrigger, options={"path": "state"})
    # changed
    assert t._event_matches(
        _data(body='{"state": "FINISH"}', previous_body='{"state": "RUNNING"}')
    ) is True
    # same
    assert t._event_matches(
        _data(body='{"state": "FINISH"}', previous_body='{"state": "FINISH"}')
    ) is False
    # first call (no previous body) counts as changed
    assert t._event_matches(_data(body='{"state": "FINISH"}', previous_body=None)) is True
    # path missing in current -> no fire
    assert t._event_matches(_data(body='{"x": 1}', previous_body='{"state": "A"}')) is False


def test_recovered() -> None:
    t = _make(trig.RecoveredTrigger)
    assert t._event_matches(_data(ok=True, status=200, previous_status=500)) is True
    assert t._event_matches(_data(ok=True, status=200, previous_status=0)) is True
    assert t._event_matches(_data(ok=True, status=200, previous_status=200)) is False
    assert t._event_matches(_data(ok=True, status=200, previous_status=None)) is False
    assert t._event_matches(_data(ok=False, status=500, previous_status=500)) is False


def test_went_down() -> None:
    t = _make(trig.WentDownTrigger)
    assert t._event_matches(_data(ok=False, status=500, previous_status=200)) is True
    assert t._event_matches(_data(ok=False, status=0, previous_status=204)) is True
    assert t._event_matches(_data(ok=True, status=200, previous_status=200)) is False
    assert t._event_matches(_data(ok=False, status=500, previous_status=None)) is False
    assert t._event_matches(_data(ok=False, status=500, previous_status=500)) is False


async def test_validate_config_content_triggers(hass: HomeAssistant) -> None:
    cfg = await trig.BodyMatchesTrigger.async_validate_config(
        hass, {"options": {"pattern": "ok"}}
    )
    assert cfg["options"]["pattern"] == "ok"

    cfg2 = await trig.ValueMatchesTrigger.async_validate_config(
        hass, {"options": {"path": "state", "equals": "FINISH"}}
    )
    assert cfg2["options"]["path"] == "state"

    # invalid regex is rejected
    with pytest.raises(vol.Invalid):
        await trig.BodyMatchesTrigger.async_validate_config(
            hass, {"options": {"pattern": "("}}
        )
    # missing required path is rejected
    with pytest.raises(vol.Invalid):
        await trig.ValueChangedTrigger.async_validate_config(hass, {"options": {}})


async def test_attach_value_matches_end_to_end(hass: HomeAssistant) -> None:
    """Full bus path for a content trigger, incl. the malformed-event guard."""
    calls: list[dict] = []
    t = _make(
        trig.ValueMatchesTrigger,
        options={"path": "state", "equals": "FINISH"},
        hass=hass,
    )
    unsub = await t.async_attach_runner(lambda p, d, c=None: calls.append(p))

    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, _data(body='{"state": "RUNNING"}'))
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_HAAPI_RESPONSE, _data(body='{"state": "FINISH"}'))
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0]["platform"] == "haapi.ValueMatchesTrigger"
    unsub()
