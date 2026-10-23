"""Tests for haapi.request per-call `variables` and `body` override."""

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi.const import (
    AUTH_BEARER,
    CONF_AUTH_TYPE,
    CONF_BEARER_TOKEN,
    CONF_BODY,
    CONF_CONTENT_TYPE,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_RETRIES,
    CONF_URL,
    DOMAIN,
)

from tests.helpers import get_endpoint_device, make_response, make_session

# Text that would leak entity state if anything rendered it a second time.
_INJECT = "x {{ states('sun.sun') }} y"

_ENDPOINT_ID = "test-endpoint-id"

# A templated endpoint: every templatable field references a per-call variable.
_URL = "https://api.example.com/say/{{ satellite | default('none') }}"
_HEADERS = "X-Urgent: {{ urgent | default(false) }}"
_BODY = '{"text": {{ message | default("") | tojson }}, "urgent": {{ urgent | default(false) | tojson }}}'
_TOKEN = "tok-{{ satellite | default('none') }}"

# >255 chars (the input_text cap this feature replaces) with every character
# that tends to break hand-built JSON: quotes, backslashes, newlines, tabs,
# HTML-ish characters, non-ASCII, and literal Jinja delimiters (which must be
# passed through as data, never rendered as a template).
_NASTY = (
    'He said "hi" \\ and left.\n\tNew line, tab; <b>&amp;</b> \'single\' '
    "café — 日本語 🐉 {{ states('sun.sun') }} {% if %} "
) + "x" * 300


@pytest.fixture
def mock_endpoint_config(mock_endpoint_config):
    """Override the shared endpoint fixture with a fully templated POST."""
    mock_endpoint_config.update(
        {
            CONF_METHOD: "POST",
            CONF_URL: _URL,
            CONF_HEADERS: _HEADERS,
            CONF_BODY: _BODY,
            CONF_CONTENT_TYPE: "application/json",
            CONF_AUTH_TYPE: AUTH_BEARER,
            CONF_BEARER_TOKEN: _TOKEN,
        }
    )
    return mock_endpoint_config


@pytest.fixture
async def loaded(hass, mock_config_entry_data, mock_config_entry_options):
    """Set up a loaded entry; return (device id, the stored endpoint config)."""
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
    device = get_endpoint_device(hass, entry.entry_id, _ENDPOINT_ID)
    assert device is not None, "HAAPI endpoint device was not created"
    caller = hass.data[DOMAIN][entry.entry_id].get_api_caller(_ENDPOINT_ID)
    return device.id, caller


async def _request(hass, device_id, **data):
    """Call haapi.request and return the kwargs passed to session.request."""
    session = make_session(make_response(200, "ok"))
    with patch("aiohttp.ClientSession", return_value=session):
        await hass.services.async_call(
            DOMAIN,
            "request",
            data,
            blocking=True,
            return_response=True,
            target={"device_id": [device_id]},
        )
    assert session.request.call_count == 1
    return session.request.call_args.kwargs


async def test_variables_render_in_url_headers_body_and_auth(
    hass: HomeAssistant, loaded
) -> None:
    device_id, _ = loaded
    kwargs = await _request(
        hass,
        device_id,
        variables={"message": "Dinner is ready", "satellite": "kitchen", "urgent": True},
    )

    assert kwargs["url"] == "https://api.example.com/say/kitchen"
    assert kwargs["json"] == {"text": "Dinner is ready", "urgent": True}
    assert kwargs["headers"]["X-Urgent"] == "True"
    assert kwargs["headers"]["Authorization"] == "Bearer tok-kitchen"
    assert kwargs["headers"]["Content-Type"] == "application/json"


async def test_body_override_replaces_configured_body(
    hass: HomeAssistant, loaded
) -> None:
    device_id, caller = loaded
    kwargs = await _request(
        hass,
        device_id,
        variables={"satellite": "kitchen"},
        body='{"override": "hello"}',
    )

    assert kwargs["json"] == {"override": "hello"}
    # variables still feed the endpoint's own templates (url, auth).
    assert kwargs["url"] == "https://api.example.com/say/kitchen"
    assert kwargs["headers"]["Authorization"] == "Bearer tok-kitchen"
    # The stored endpoint is untouched by the per-call override.
    assert caller.endpoint_config[CONF_BODY] == _BODY


async def test_body_override_is_not_rendered_again(
    hass: HomeAssistant, loaded
) -> None:
    """The override is final text: template syntax inside it is sent
    literally, never evaluated (no double rendering / template injection)."""
    hass.states.async_set("sun.sun", "above_horizon")
    device_id, _ = loaded
    body = '{"text": "' + _INJECT + '", "m": "{{ message }}"}'
    kwargs = await _request(
        hass, device_id, variables={"message": "SHOULD-NOT-APPEAR"}, body=body
    )

    assert kwargs["json"] == {"text": _INJECT, "m": "{{ message }}"}
    assert "above_horizon" not in str(kwargs)


async def test_empty_body_override_uses_configured_body(
    hass: HomeAssistant, loaded
) -> None:
    """A blank body field means "not set", same as omitting it."""
    device_id, _ = loaded
    kwargs = await _request(hass, device_id, variables={"message": "hi"}, body="")
    assert kwargs["json"] == {"text": "hi", "urgent": False}


async def test_bool_body_override_is_json(hass: HomeAssistant, loaded) -> None:
    """bool is an int subclass; it must be sent as JSON true, not "True"."""
    device_id, _ = loaded
    kwargs = await _request(hass, device_id, body=True)
    assert kwargs["json"] is True


async def test_body_override_as_prerendered_mapping(
    hass: HomeAssistant, loaded
) -> None:
    """HA renders templates in action data first; a JSON string arrives as a
    dict. It must be re-serialized, not str()'d into Python repr."""
    device_id, _ = loaded
    kwargs = await _request(hass, device_id, body={"a": 1, "b": "x y"})
    assert kwargs["json"] == {"a": 1, "b": "x y"}


async def test_omitted_fields_match_old_behaviour(
    hass: HomeAssistant, loaded
) -> None:
    """No variables/body -> exactly what the Trigger button sends (the
    pre-feature behaviour), and per-call variables never leak into later calls."""
    device_id, caller = loaded
    before = dict(caller.endpoint_config)

    plain = await _request(hass, device_id)
    await _request(hass, device_id, variables={"message": "leak?", "satellite": "x"})
    after = await _request(hass, device_id)

    session = make_session(make_response(200, "ok"))
    with patch("aiohttp.ClientSession", return_value=session):
        await hass.services.async_call(
            "button", "press", blocking=True, target={"device_id": [device_id]}
        )
    pressed = session.request.call_args.kwargs

    assert plain == pressed == after
    assert plain["url"] == "https://api.example.com/say/none"
    assert plain["json"] == {"text": "", "urgent": False}
    assert caller.endpoint_config == before


async def test_long_special_text_passes_through_intact(
    hass: HomeAssistant, loaded
) -> None:
    assert len(_NASTY) > 255
    device_id, _ = loaded
    kwargs = await _request(hass, device_id, variables={"message": _NASTY})

    # The JSON body parsed cleanly (sent as json=, not the text fallback) and
    # the value is byte-for-byte what the caller passed, Jinja delimiters and all.
    assert "data" not in kwargs
    assert kwargs["json"]["text"] == _NASTY


async def test_variables_from_a_templated_automation_action(
    hass: HomeAssistant, loaded
) -> None:
    """The real voice-automation shape: variables templated from run vars."""
    device_id, _ = loaded
    script = Script(
        hass,
        cv.SCRIPT_SCHEMA([
            {
                "action": "haapi.request",
                "target": {"device_id": device_id},
                "data": {
                    "variables": {
                        "message": "{{ msg }}",
                        "satellite": "{{ sat }}",
                        "urgent": "{{ is_urgent }}",
                    }
                },
            }
        ]),
        "test",
        DOMAIN,
    )
    session = make_session(make_response(200, "ok"))
    with patch("aiohttp.ClientSession", return_value=session):
        await script.async_run(
            run_variables={"msg": _NASTY, "sat": "office", "is_urgent": True},
            context=Context(),
        )
        await hass.async_block_till_done()

    kwargs = session.request.call_args.kwargs
    assert kwargs["url"] == "https://api.example.com/say/office"
    assert kwargs["json"] == {"text": _NASTY, "urgent": True}


async def test_body_from_a_templated_automation_action(
    hass: HomeAssistant, loaded
) -> None:
    """A body templated in the automation is rendered by HA exactly once:
    template syntax inside the run variable's *value* stays literal."""
    hass.states.async_set("sun.sun", "above_horizon")
    device_id, caller = loaded
    script = Script(
        hass,
        cv.SCRIPT_SCHEMA([
            {
                "action": "haapi.request",
                "target": {"device_id": device_id},
                "data": {"body": '{"text": {{ msg | tojson }}}'},
            }
        ]),
        "test",
        DOMAIN,
    )
    session = make_session(make_response(200, "ok"))
    with patch("aiohttp.ClientSession", return_value=session):
        await script.async_run(run_variables={"msg": _INJECT}, context=Context())
        await hass.async_block_till_done()

    kwargs = session.request.call_args.kwargs
    assert kwargs["json"] == {"text": _INJECT}
    assert "above_horizon" not in str(kwargs)
    assert caller.endpoint_config[CONF_BODY] == _BODY


async def test_concurrent_requests_each_get_their_own_response(
    hass: HomeAssistant, loaded
) -> None:
    """Two overlapping calls on one endpoint: each service response must
    reflect its own HTTP result even though the shared last_response_* state
    is overwritten by the other call while the first awaits storage."""
    device_id, caller = loaded
    release = asyncio.Event()
    saves_started = 0

    async def _blocked_save() -> None:
        nonlocal saves_started
        saves_started += 1
        await release.wait()

    caller._save_callback = _blocked_save
    session = make_session(
        make_response(200, "first", {"X-Call": "1"}),
        make_response(503, "second", {"X-Call": "2"}),
    )

    async def _call():
        return await hass.services.async_call(
            DOMAIN,
            "request",
            {},
            blocking=True,
            return_response=True,
            target={"device_id": [device_id]},
        )

    with patch("aiohttp.ClientSession", return_value=session), patch.object(
        caller, "endpoint_config", {**caller.endpoint_config, CONF_RETRIES: 0}
    ):
        first = hass.async_create_task(_call())
        while saves_started < 1:
            await asyncio.sleep(0)
        second = hass.async_create_task(_call())
        while saves_started < 2:
            await asyncio.sleep(0)
        # Both calls have now written the shared state; the second won.
        assert caller.last_response_body == "second"
        release.set()
        r1, r2 = await first, await second

    assert (r1["status"], r1["ok"], r1["body"], r1["headers"]) == (
        200, True, "first", {"X-Call": "1"}
    )
    assert (r2["status"], r2["ok"], r2["body"], r2["headers"]) == (
        503, False, "second", {"X-Call": "2"}
    )
    # Sensors/storage still see the most recent result, as before.
    assert caller.last_response_code == 503


@pytest.mark.parametrize(
    ("data", "match"),
    [
        ({"variables": "message=hi"}, "variables"),
        ({"body": None, "variables": ["x"]}, "variables"),
        ({"body": object()}, "body"),
    ],
)
async def test_invalid_fields_raise(hass: HomeAssistant, loaded, data, match) -> None:
    device_id, _ = loaded
    with pytest.raises(ServiceValidationError, match=match):
        await hass.services.async_call(
            DOMAIN,
            "request",
            data,
            blocking=True,
            return_response=True,
            target={"device_id": [device_id]},
        )

