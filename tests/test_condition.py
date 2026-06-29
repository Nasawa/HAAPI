"""Tests for the HAAPI condition platform."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.condition import ConditionConfig
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi import condition as cond
from custom_components.haapi.const import DOMAIN

_ENDPOINT_ID = "test-endpoint-id"


@pytest.fixture
async def endpoint(hass, mock_config_entry_data, mock_config_entry_options):
    """Set up a loaded entry and return its api caller + device id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=mock_config_entry_options,
        version=2,
    )
    entry.add_to_hass(hass)
    with patch("custom_components.haapi.Store.async_load", return_value={}):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    caller = coordinator.get_api_caller(_ENDPOINT_ID)
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_{_ENDPOINT_ID}")}
    )
    return SimpleNamespace(caller=caller, device_id=device.id)


def _make(cls, device_id, options=None):
    return cls(
        None,
        ConditionConfig(options=options or {}, target={"device_id": [device_id]}),
    )


def _set_response(caller, code, body=None):
    caller._last_response_code = code
    caller._last_response_body = body


async def test_get_conditions(hass: HomeAssistant) -> None:
    conditions = await cond.async_get_conditions(hass)
    assert set(conditions) == {
        "last_call_succeeded",
        "response_contains",
        "value_is",
    }


async def test_last_call_succeeded(hass: HomeAssistant, endpoint) -> None:
    c = _make(cond.LastCallSucceededCondition, endpoint.device_id)
    c._hass = hass
    check = await c.async_get_checker()

    _set_response(endpoint.caller, 200, "ok")
    assert check(hass, {}) is True
    _set_response(endpoint.caller, 500, "err")
    assert check(hass, {}) is False
    _set_response(endpoint.caller, None, None)
    assert check(hass, {}) is False


async def test_response_contains(hass: HomeAssistant, endpoint) -> None:
    c = _make(
        cond.ResponseContainsCondition,
        endpoint.device_id,
        options={"pattern": r'"state":\s*"FINISH"'},
    )
    c._hass = hass
    check = await c.async_get_checker()

    _set_response(endpoint.caller, 200, '{"state": "FINISH"}')
    assert check(hass, {}) is True
    _set_response(endpoint.caller, 200, '{"state": "RUNNING"}')
    assert check(hass, {}) is False
    _set_response(endpoint.caller, 200, None)
    assert check(hass, {}) is False


async def test_value_is(hass: HomeAssistant, endpoint) -> None:
    c = _make(
        cond.ValueIsCondition,
        endpoint.device_id,
        options={"path": "state", "equals": "FINISH"},
    )
    c._hass = hass
    check = await c.async_get_checker()

    _set_response(endpoint.caller, 200, '{"state": "FINISH"}')
    assert check(hass, {}) is True
    _set_response(endpoint.caller, 200, '{"state": "RUNNING"}')
    assert check(hass, {}) is False
    _set_response(endpoint.caller, 200, '{"other": 1}')  # path missing
    assert check(hass, {}) is False


async def test_value_is_json_spelling(hass: HomeAssistant, endpoint) -> None:
    c = _make(
        cond.ValueIsCondition,
        endpoint.device_id,
        options={"path": "connected", "equals": "true"},
    )
    c._hass = hass
    check = await c.async_get_checker()
    _set_response(endpoint.caller, 200, '{"connected": true}')
    assert check(hass, {}) is True


async def test_checker_false_when_target_unresolvable(hass: HomeAssistant) -> None:
    """No matching HAAPI device -> condition is False, not an error."""
    c = _make(cond.LastCallSucceededCondition, "does-not-exist")
    c._hass = hass
    check = await c.async_get_checker()
    assert check(hass, {}) is False


async def test_validate_config(hass: HomeAssistant) -> None:
    cfg = await cond.ResponseContainsCondition.async_validate_config(
        hass, {"target": {"device_id": ["x"]}, "options": {"pattern": "ok"}}
    )
    assert cfg["options"]["pattern"] == "ok"

    with pytest.raises(vol.Invalid):
        await cond.ResponseContainsCondition.async_validate_config(
            hass, {"target": {"device_id": ["x"]}, "options": {"pattern": "("}}
        )
    with pytest.raises(vol.Invalid):
        await cond.ValueIsCondition.async_validate_config(
            hass, {"target": {"device_id": ["x"]}, "options": {}}
        )
