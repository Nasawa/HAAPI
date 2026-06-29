"""Tests for the HAAPI request service."""

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi.const import (
    ATTR_BODY,
    ATTR_ENDPOINT_NAME,
    ATTR_OK,
    ATTR_STATUS,
    DOMAIN,
)

from tests.helpers import make_response, make_session

_ENDPOINT_ID = "test-endpoint-id"


@pytest.fixture
async def loaded(hass, mock_config_entry_data, mock_config_entry_options):
    """Set up a loaded entry; return its device id."""
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
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_{_ENDPOINT_ID}")}
    )
    assert device is not None, "HAAPI endpoint device was not created"
    return device.id


async def test_request_returns_response(hass: HomeAssistant, loaded) -> None:
    session = make_session(
        make_response(200, '{"state": "FINISH"}', {"Content-Type": "application/json"})
    )
    with patch("aiohttp.ClientSession", return_value=session):
        # Call via target= (the real-automation path: HA merges target into
        # call.data), not service_data, so this exercises how it's actually used.
        result = await hass.services.async_call(
            DOMAIN,
            "request",
            blocking=True,
            return_response=True,
            target={"device_id": [loaded]},
        )

    assert result[ATTR_STATUS] == 200
    assert result[ATTR_OK] is True
    assert result[ATTR_BODY] == '{"state": "FINISH"}'
    assert result[ATTR_ENDPOINT_NAME] == "Test Endpoint"


async def test_request_without_capturing_response(hass: HomeAssistant, loaded) -> None:
    """The action is OPTIONAL-response: a fire-and-forget call (no
    return_response / response_variable) must succeed, not error.

    This is the clear-plate case — without it, SupportsResponse.ONLY would make
    HA reject the call ("requires response_variable").
    """
    session = make_session(make_response(204, ""))
    with patch("aiohttp.ClientSession", return_value=session):
        result = await hass.services.async_call(
            DOMAIN,
            "request",
            blocking=True,
            target={"device_id": [loaded]},
        )

    # No response requested -> None returned, but the call still happened.
    assert result is None
    assert session.request.called


async def test_request_unresolvable_target_raises(hass: HomeAssistant, loaded) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "request",
            blocking=True,
            return_response=True,
            target={"device_id": ["does-not-exist"]},
        )
