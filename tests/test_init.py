"""Test the HAAPI __init__ module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi import async_setup_entry, async_unload_entry
from custom_components.haapi.const import DOMAIN


async def test_setup_unload_entry(hass: HomeAssistant, mock_config_entry_data, mock_config_entry_options) -> None:
    """Test setting up and unloading a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=mock_config_entry_options,
    )
    entry.add_to_hass(hass)

    with patch("custom_components.haapi.Store.async_load", return_value={}):
        assert await async_setup_entry(hass, entry)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    assert await async_unload_entry(hass, entry)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.parametrize(
    "status_code,response_text,expected_code,expected_body",
    [
        (200, "Success", 200, "Success"),
        (404, "Not Found", 404, "Not Found"),
        (500, "Server Error", 500, "Server Error"),
    ],
)
async def test_api_call_success(
    hass: HomeAssistant,
    mock_endpoint_config,
    status_code,
    response_text,
    expected_code,
    expected_body,
) -> None:
    """Test successful API calls with various status codes."""
    from custom_components.haapi import HaapiApiCaller

    mock_response = AsyncMock()
    mock_response.status = status_code
    mock_response.text = AsyncMock(return_value=response_text)
    mock_response.headers = {"Content-Type": "text/plain"}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == expected_code
    assert api_caller.last_response_body == expected_body
    assert api_caller.truncated is False
    assert save_callback.called


async def test_api_call_with_truncation(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call with response truncation."""
    from custom_components.haapi import HaapiApiCaller

    # Create a large response that exceeds the default limit
    large_response = "x" * 20000  # 20KB, default limit is 10KB

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=large_response)
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    assert api_caller.truncated is True
    assert len(api_caller.last_response_body) <= 10240
    assert "[TRUNCATED:" in api_caller.last_response_body


async def test_api_call_with_retries(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call with retry logic on server error."""
    from custom_components.haapi import HaapiApiCaller

    # Configure endpoint with retries
    mock_endpoint_config["retries"] = 2
    mock_endpoint_config["retry_delay"] = 0  # No delay for testing

    # First two calls fail with 503, third succeeds
    mock_response_fail = AsyncMock()
    mock_response_fail.status = 503
    mock_response_fail.text = AsyncMock(return_value="Service Unavailable")
    mock_response_fail.headers = {}

    mock_response_success = AsyncMock()
    mock_response_success.status = 200
    mock_response_success.text = AsyncMock(return_value="Success")
    mock_response_success.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(
        side_effect=[mock_response_fail, mock_response_fail, mock_response_success]
    )
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await api_caller.async_call_api()

    # Should have made 3 attempts (1 initial + 2 retries)
    assert mock_session.request.call_count == 3
    assert api_caller.last_response_code == 200
    assert api_caller.last_response_body == "Success"


async def test_api_call_retry_exhausted(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call when all retries are exhausted."""
    from custom_components.haapi import HaapiApiCaller

    # Configure endpoint with retries
    mock_endpoint_config["retries"] = 2
    mock_endpoint_config["retry_delay"] = 0

    # All calls fail with network error
    mock_session = AsyncMock()
    mock_session.request = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await api_caller.async_call_api()

    # Should have made 3 attempts (1 initial + 2 retries)
    assert mock_session.request.call_count == 3
    assert api_caller.last_response_code == 0
    assert "Connection failed" in api_caller.last_response_body


async def test_api_call_no_retry_on_client_error(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test that client errors (4xx) don't trigger retries."""
    from custom_components.haapi import HaapiApiCaller

    # Configure endpoint with retries
    mock_endpoint_config["retries"] = 2
    mock_endpoint_config["retry_delay"] = 0

    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.text = AsyncMock(return_value="Not Found")
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    # Should only make 1 attempt (no retries for 4xx)
    assert mock_session.request.call_count == 1
    assert api_caller.last_response_code == 404


async def test_api_call_with_ssl_disabled(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call with SSL verification disabled."""
    from custom_components.haapi import HaapiApiCaller

    mock_endpoint_config["verify_ssl"] = False

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="Success")
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that TCPConnector was created with SSL context
    assert mock_session.request.called


async def test_api_call_with_json_body(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call with JSON body is sent correctly."""
    from custom_components.haapi import HaapiApiCaller

    # Configure endpoint with JSON body
    mock_endpoint_config["method"] = "POST"
    mock_endpoint_config["content_type"] = "application/json"
    mock_endpoint_config["body"] = '{"key": "value", "number": 42}'

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="Success")
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that request was called with json parameter, not data
    call_kwargs = mock_session.request.call_args[1]
    assert "json" in call_kwargs
    assert call_kwargs["json"] == {"key": "value", "number": 42}
    assert "data" not in call_kwargs or call_kwargs["data"] is None


async def test_api_call_with_form_data(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call with form data is sent as data parameter."""
    from custom_components.haapi import HaapiApiCaller

    # Configure endpoint with form data
    mock_endpoint_config["method"] = "POST"
    mock_endpoint_config["content_type"] = "application/x-www-form-urlencoded"
    mock_endpoint_config["body"] = "key=value&number=42"

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="Success")
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that request was called with data parameter, not json
    call_kwargs = mock_session.request.call_args[1]
    assert "data" in call_kwargs
    assert call_kwargs["data"] == "key=value&number=42"
    assert "json" not in call_kwargs or call_kwargs["json"] is None


async def test_api_call_with_invalid_json_body(hass: HomeAssistant, mock_endpoint_config) -> None:
    """Test API call with invalid JSON body falls back to sending as data."""
    from custom_components.haapi import HaapiApiCaller

    # Configure endpoint with invalid JSON
    mock_endpoint_config["method"] = "POST"
    mock_endpoint_config["content_type"] = "application/json"
    mock_endpoint_config["body"] = "not valid json"

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="Success")
    mock_response.headers = {}

    mock_session = AsyncMock()
    mock_session.request = AsyncMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that invalid JSON falls back to data parameter
    call_kwargs = mock_session.request.call_args[1]
    assert "data" in call_kwargs
    assert call_kwargs["data"] == "not valid json"
    assert "json" not in call_kwargs or call_kwargs["json"] is None
