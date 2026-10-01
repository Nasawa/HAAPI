"""Load HAAPI conditions (and triggers) through Home Assistant's own machinery.

The unit tests in ``test_condition.py`` call the condition classes directly,
which is how HAAPI's conditions shipped broken on HA 2026.5+ without any test
noticing: HA's ``Condition`` base class changed contract (``_async_check``
became abstract), so HA could no longer instantiate them. These tests go
through ``condition.async_validate_condition_config`` /
``condition.async_from_config`` and a real automation, exactly like a user's
config does, so a base-class contract change fails here on any HA version.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.components import automation
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition as ha_condition
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.haapi.const import DOMAIN

from tests.helpers import get_endpoint_device

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
    device = get_endpoint_device(hass, entry.entry_id, _ENDPOINT_ID)
    assert device is not None, "HAAPI endpoint device was not created"
    return SimpleNamespace(caller=caller, device_id=device.id)


def _set_response(caller, code, body=None):
    caller._last_response_code = code
    caller._last_response_body = body


async def _load(hass: HomeAssistant, config: dict):
    """Validate + build a condition checker the way HA does for automations."""
    validated = await ha_condition.async_validate_condition_config(hass, config)
    return await ha_condition.async_from_config(hass, validated)


@pytest.mark.parametrize(
    ("config", "passing", "failing"),
    [
        (
            {"condition": "haapi.last_call_succeeded"},
            (200, "ok"),
            (500, "err"),
        ),
        (
            {
                "condition": "haapi.response_contains",
                "options": {"pattern": r'"state":\s*"FINISH"'},
            },
            (200, '{"state": "FINISH"}'),
            (200, '{"state": "RUNNING"}'),
        ),
        (
            {
                "condition": "haapi.value_is",
                "options": {"path": "state", "equals": "FINISH"},
            },
            (200, '{"state": "FINISH"}'),
            (200, '{"other": 1}'),
        ),
    ],
)
async def test_conditions_load_and_evaluate_via_ha(
    hass: HomeAssistant, endpoint, config, passing, failing
) -> None:
    """Every HAAPI condition loads through HA's loader and evaluates live."""
    check = await _load(
        hass, {**config, "target": {"device_id": [endpoint.device_id]}}
    )

    _set_response(endpoint.caller, *passing)
    assert check(hass, {}) is True
    _set_response(endpoint.caller, *failing)
    assert check(hass, {}) is False
    _set_response(endpoint.caller, None, None)
    assert check(hass, {}) is False


async def test_invalid_condition_config_disables_only_that_automation(
    hass: HomeAssistant, endpoint
) -> None:
    """A bad regex is a clean config error: that automation is disabled, the
    rest load. (HA 2026.10 moved its validation to ``probatio``; this proves
    HAAPI's schema errors are still recognised as validation errors.)"""
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "id": "haapi_bad_condition",
                    "alias": "HAAPI bad condition",
                    "triggers": {"trigger": "event", "event_type": "haapi_test_go"},
                    "conditions": {
                        "condition": "haapi.response_contains",
                        "target": {"device_id": [endpoint.device_id]},
                        "options": {"pattern": "("},
                    },
                    "actions": {"event": "haapi_test_unused"},
                },
                {
                    "id": "haapi_unrelated",
                    "alias": "HAAPI unrelated",
                    "triggers": {"trigger": "event", "event_type": "haapi_test_go"},
                    "actions": {"event": "haapi_test_unused"},
                },
            ]
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get("automation.haapi_bad_condition").state == "unavailable"
    assert hass.states.get("automation.haapi_unrelated").state == "on"


async def test_condition_gates_a_real_automation(
    hass: HomeAssistant, endpoint
) -> None:
    """End to end: an automation using a HAAPI condition loads and gates."""
    passed = async_capture_events(hass, "haapi_test_condition_passed")
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "id": "haapi_condition_e2e",
                "alias": "HAAPI condition e2e",
                "triggers": {"trigger": "event", "event_type": "haapi_test_go"},
                "conditions": {
                    "condition": "haapi.last_call_succeeded",
                    "target": {"device_id": [endpoint.device_id]},
                },
                "actions": {"event": "haapi_test_condition_passed"},
            }
        },
    )
    await hass.async_block_till_done()
    # The automation must have loaded (an unloadable condition leaves it
    # unavailable rather than raising).
    state = hass.states.get("automation.haapi_condition_e2e")
    assert state is not None
    assert state.state == "on"

    _set_response(endpoint.caller, 500, "err")
    hass.bus.async_fire("haapi_test_go")
    await hass.async_block_till_done()
    assert len(passed) == 0

    _set_response(endpoint.caller, 200, "ok")
    hass.bus.async_fire("haapi_test_go")
    await hass.async_block_till_done()
    assert len(passed) == 1


async def test_trigger_and_condition_in_one_real_automation(
    hass: HomeAssistant, endpoint
) -> None:
    """HAAPI trigger + HAAPI condition load together through HA's loader.

    Guards the trigger platform against the same class of base-class contract
    change that broke the conditions.
    """
    fired = async_capture_events(hass, "haapi_test_trigger_fired")
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "id": "haapi_trigger_e2e",
                "alias": "HAAPI trigger e2e",
                "triggers": {
                    "trigger": "haapi.response_received",
                    "target": {"device_id": [endpoint.device_id]},
                },
                "conditions": {
                    "condition": "haapi.value_is",
                    "target": {"device_id": [endpoint.device_id]},
                    "options": {"path": "state", "equals": "FINISH"},
                },
                "actions": {"event": "haapi_test_trigger_fired"},
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get("automation.haapi_trigger_e2e").state == "on"

    _set_response(endpoint.caller, 200, '{"state": "RUNNING"}')
    endpoint.caller._fire_response_event(None, None)
    await hass.async_block_till_done()
    assert len(fired) == 0  # triggered, but the condition gated it

    _set_response(endpoint.caller, 200, '{"state": "FINISH"}')
    endpoint.caller._fire_response_event(200, '{"state": "RUNNING"}')
    await hass.async_block_till_done()
    assert len(fired) == 1
