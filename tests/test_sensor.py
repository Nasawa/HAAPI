"""Test the HAAPI sensor platform."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi.const import (
    ATTR_MAX_RESPONSE_SIZE,
    ATTR_RETRIES,
    ATTR_RETRY_DELAY,
    ATTR_TIMEOUT,
    ATTR_TRUNCATED,
    ATTR_URL,
    ATTR_VERIFY_SSL,
    DOMAIN,
)


async def test_request_sensor(hass: HomeAssistant, mock_config_entry_data, mock_config_entry_options) -> None:
    """Test request sensor shows endpoint configuration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=mock_config_entry_options,
    )
    entry.add_to_hass(hass)

    with patch("custom_components.haapi.Store.async_load", return_value={}):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Get the request sensor
    request_sensor_id = f"sensor.test_endpoint_request"
    state = hass.states.get(request_sensor_id)
    assert state is not None
    assert state.state == "GET"  # Default method

    # Check attributes
    attrs = state.attributes
    assert ATTR_URL in attrs
    assert attrs[ATTR_URL] == "https://api.example.com/test"
    assert attrs[ATTR_TIMEOUT] == 10
    assert attrs[ATTR_VERIFY_SSL] is True
    assert attrs[ATTR_MAX_RESPONSE_SIZE] == 10240
    assert attrs[ATTR_RETRIES] == 0
    assert attrs[ATTR_RETRY_DELAY] == 1


async def test_response_sensor(hass: HomeAssistant, mock_config_entry_data, mock_config_entry_options) -> None:
    """Test response sensor shows API response."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=mock_config_entry_options,
    )
    entry.add_to_hass(hass)

    with patch("custom_components.haapi.Store.async_load", return_value={}):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Get the response sensor
    response_sensor_id = f"sensor.test_endpoint_response"
    state = hass.states.get(response_sensor_id)
    assert state is not None

    # Initially should have no response
    assert state.state is None or state.state == "unknown"

    # Simulate an API call
    coordinator = hass.data[DOMAIN][entry.entry_id]
    endpoint_id = mock_config_entry_options["endpoints"][0]["id"]
    api_caller = coordinator.get_api_caller(endpoint_id)

    # Mock a successful response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value='{"result": "success"}')
    mock_response.headers = {"Content-Type": "application/json"}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()
        await hass.async_block_till_done()

    # Check updated sensor state
    state = hass.states.get(response_sensor_id)
    assert state.state == "200"

    # Check response attributes
    attrs = state.attributes
    assert "response_body" in attrs
    assert attrs["response_body"] == '{"result": "success"}'
    assert ATTR_TRUNCATED in attrs
    assert attrs[ATTR_TRUNCATED] is False


async def test_response_sensor_with_truncation(
    hass: HomeAssistant, mock_config_entry_data, mock_endpoint_config
) -> None:
    """Test response sensor shows truncated flag when response is truncated."""
    # Configure a small max response size
    mock_endpoint_config["max_response_size"] = 100

    options = {"endpoints": [mock_endpoint_config]}
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=options,
    )
    entry.add_to_hass(hass)

    with patch("custom_components.haapi.Store.async_load", return_value={}):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Simulate an API call with large response
    coordinator = hass.data[DOMAIN][entry.entry_id]
    endpoint_id = mock_endpoint_config["id"]
    api_caller = coordinator.get_api_caller(endpoint_id)

    large_response = "x" * 500  # 500 bytes, exceeds 100 byte limit

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=large_response)
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()
        await hass.async_block_till_done()

    # Check sensor shows truncated
    response_sensor_id = f"sensor.test_endpoint_response"
    state = hass.states.get(response_sensor_id)
    assert state.state == "200"

    attrs = state.attributes
    assert attrs[ATTR_TRUNCATED] is True
    assert "[TRUNCATED:" in attrs["response_body"]
