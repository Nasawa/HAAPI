"""Test the HAAPI __init__ module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi.const import DOMAIN


async def test_setup_unload_entry(hass: HomeAssistant, mock_config_entry_data, mock_config_entry_options) -> None:
    """Test setting up and unloading a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options=mock_config_entry_options,
        version=2,
    )
    entry.add_to_hass(hass)

    # Go through the config-entries state machine; modern HA requires the entry
    # to be LOADED before platforms can be forwarded (a direct async_setup_entry
    # call leaves it NOT_LOADED).
    with patch("custom_components.haapi.Store.async_load", return_value={}):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
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

    mock_session = make_session(mock_response)

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

    mock_session = make_session(mock_response)

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

    mock_session = make_session(
        mock_response_fail, mock_response_fail, mock_response_success
    )

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
    mock_session = make_session(raise_exc=aiohttp.ClientError("Connection failed"))

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

    mock_session = make_session(mock_response)

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

    mock_session = make_session(mock_response)

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

    mock_session = make_session(mock_response)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that request was called with json parameter, not data
    call_kwargs = mock_session.request.call_args[1]
    assert "json" in call_kwargs
    assert call_kwargs["json"] == {"key": "value", "number": 42}
    assert call_kwargs.get("data") is None


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

    mock_session = make_session(mock_response)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that request was called with data parameter, not json
    call_kwargs = mock_session.request.call_args[1]
    assert "data" in call_kwargs
    assert call_kwargs["data"] == "key=value&number=42"
    assert call_kwargs.get("json") is None


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

    mock_session = make_session(mock_response)

    save_callback = AsyncMock()
    api_caller = HaapiApiCaller(hass, mock_endpoint_config, {}, save_callback)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await api_caller.async_call_api()

    assert api_caller.last_response_code == 200
    # Verify that invalid JSON falls back to data parameter
    call_kwargs = mock_session.request.call_args[1]
    assert "data" in call_kwargs
    assert call_kwargs["data"] == "not valid json"
    assert call_kwargs.get("json") is None


# ---------------------------------------------------------------------------
# haapi_response event + change detection (integration triggers, 2.7.0)
# ---------------------------------------------------------------------------

from pytest_homeassistant_custom_component.common import async_capture_events  # noqa: E402

from custom_components.haapi.const import (  # noqa: E402
    ATTR_BODY,
    ATTR_BODY_CHANGED,
    ATTR_ENDPOINT_ID,
    ATTR_ENDPOINT_NAME,
    ATTR_ENTRY_ID,
    ATTR_OK,
    ATTR_PREVIOUS_STATUS,
    ATTR_STATUS,
    ATTR_STATUS_CHANGED,
    EVENT_HAAPI_RESPONSE,
)


from tests.helpers import make_session  # noqa: E402
from tests.helpers import mock_client_session as _mock_client_session  # noqa: E402


async def test_response_event_fired(hass: HomeAssistant, mock_endpoint_config) -> None:
    """A completed call fires haapi_response with the expected payload."""
    from custom_components.haapi import HaapiApiCaller

    events = async_capture_events(hass, EVENT_HAAPI_RESPONSE)
    api_caller = HaapiApiCaller(
        hass, mock_endpoint_config, {}, AsyncMock(), entry_id="entry-1"
    )

    session = _mock_client_session(200, "hello", {"Content-Type": "text/plain"})
    with patch("aiohttp.ClientSession", return_value=session):
        await api_caller.async_call_api()
    await hass.async_block_till_done()

    assert len(events) == 1
    data = events[0].data
    assert data[ATTR_ENTRY_ID] == "entry-1"
    assert data[ATTR_ENDPOINT_ID] == "test-endpoint-id"
    assert data[ATTR_ENDPOINT_NAME] == "Test Endpoint"
    assert data[ATTR_STATUS] == 200
    assert data[ATTR_OK] is True
    assert data[ATTR_BODY] == "hello"
    # First-ever call: no prior values, so both register as changed.
    assert data[ATTR_STATUS_CHANGED] is True
    assert data[ATTR_BODY_CHANGED] is True
    assert data[ATTR_PREVIOUS_STATUS] is None


async def test_change_detection_across_calls(
    hass: HomeAssistant, mock_endpoint_config
) -> None:
    """status_changed / body_changed reflect diffs vs. the previous call."""
    from custom_components.haapi import HaapiApiCaller

    events = async_capture_events(hass, EVENT_HAAPI_RESPONSE)
    api_caller = HaapiApiCaller(
        hass, mock_endpoint_config, {}, AsyncMock(), entry_id="entry-1"
    )

    async def _call(status, body):
        with patch(
            "aiohttp.ClientSession",
            return_value=_mock_client_session(status, body),
        ):
            await api_caller.async_call_api()
        await hass.async_block_till_done()

    await _call(200, "A")  # first
    await _call(200, "A")  # identical
    await _call(200, "B")  # body changed only
    await _call(500, "B")  # status changed only

    assert [e.data[ATTR_STATUS_CHANGED] for e in events] == [True, False, False, True]
    assert [e.data[ATTR_BODY_CHANGED] for e in events] == [True, False, True, False]
    assert [e.data[ATTR_OK] for e in events] == [True, True, True, False]
    assert events[3].data[ATTR_PREVIOUS_STATUS] == 200


async def test_failed_call_fires_event(hass: HomeAssistant, mock_endpoint_config) -> None:
    """A network error still fires the event with status 0 / ok False."""
    from custom_components.haapi import HaapiApiCaller

    events = async_capture_events(hass, EVENT_HAAPI_RESPONSE)
    api_caller = HaapiApiCaller(
        hass, mock_endpoint_config, {}, AsyncMock(), entry_id="entry-1"
    )

    req_cm = MagicMock()
    req_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("boom"))
    req_cm.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.request = MagicMock(return_value=req_cm)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=session):
        await api_caller.async_call_api()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data[ATTR_STATUS] == 0
    assert events[0].data[ATTR_OK] is False
