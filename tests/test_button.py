"""Test the HAAPI button platform."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi.const import DOMAIN


async def test_button_press(hass: HomeAssistant, mock_config_entry_data, mock_config_entry_options) -> None:
    """Test button press triggers API call."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=mock_config_entry_options,
    )
    entry.add_to_hass(hass)

    with patch("custom_components.haapi.Store.async_load", return_value={}):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Get the button entity
    button_entity_id = f"button.test_endpoint_trigger"
    state = hass.states.get(button_entity_id)
    assert state is not None

    # Mock the API caller's async_call_api method
    coordinator = hass.data[DOMAIN][entry.entry_id]
    endpoint_id = mock_config_entry_options["endpoints"][0]["id"]
    api_caller = coordinator.get_api_caller(endpoint_id)

    with patch.object(api_caller, "async_call_api", new_callable=AsyncMock) as mock_call:
        # Press the button
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": button_entity_id},
            blocking=True,
        )

        # Verify API was called
        mock_call.assert_called_once()
