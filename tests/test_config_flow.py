"""Test the HAAPI config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haapi.const import (
    CONF_AUTH_TYPE,
    CONF_BODY,
    CONF_CONTENT_TYPE,
    CONF_ENDPOINT_ID,
    CONF_ENDPOINT_NAME,
    CONF_ENDPOINTS,
    CONF_HEADERS,
    CONF_MAX_RESPONSE_SIZE,
    CONF_METHOD,
    CONF_RETRIES,
    CONF_RETRY_DELAY,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_MAX_RESPONSE_SIZE,
    DEFAULT_METHOD,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test HAAPI",
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test HAAPI"
    assert result2["data"] == {}
    assert result2["options"] == {CONF_ENDPOINTS: []}


async def test_options_add_endpoint(hass: HomeAssistant, mock_config_entry_data) -> None:
    """Test adding an endpoint through options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options={CONF_ENDPOINTS: []},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "add_endpoint"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "add_endpoint"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {
            CONF_ENDPOINT_NAME: "Test API",
            CONF_URL: "https://api.example.com/data",
            CONF_METHOD: "POST",
            CONF_HEADERS: "X-Test: value",
            CONF_BODY: '{"test": true}',
            CONF_CONTENT_TYPE: "application/json",
            CONF_TIMEOUT: 15,
            CONF_VERIFY_SSL: True,
            CONF_MAX_RESPONSE_SIZE: 50000,
            CONF_RETRIES: 2,
            CONF_RETRY_DELAY: 3,
        },
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "add_endpoint_auth"

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"],
        {
            CONF_AUTH_TYPE: "none",
        },
    )
    assert result4["type"] == FlowResultType.CREATE_ENTRY

    endpoints = result4["data"][CONF_ENDPOINTS]
    assert len(endpoints) == 1
    assert endpoints[0][CONF_ENDPOINT_NAME] == "Test API"
    assert endpoints[0][CONF_URL] == "https://api.example.com/data"
    assert endpoints[0][CONF_METHOD] == "POST"
    assert endpoints[0][CONF_TIMEOUT] == 15
    assert endpoints[0][CONF_RETRIES] == 2
    assert endpoints[0][CONF_RETRY_DELAY] == 3


async def test_options_edit_endpoint(hass: HomeAssistant, mock_config_entry_data, mock_endpoint_config) -> None:
    """Test editing an endpoint through options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options={CONF_ENDPOINTS: [mock_endpoint_config]},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "edit_endpoint"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "edit_endpoint"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {"endpoint": mock_endpoint_config[CONF_ENDPOINT_ID]},
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "edit_endpoint_config"

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"],
        {
            CONF_ENDPOINT_NAME: "Updated Test Endpoint",
            CONF_URL: "https://api.example.com/updated",
            CONF_METHOD: "PUT",
            CONF_HEADERS: "",
            CONF_BODY: "",
            CONF_CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
            CONF_TIMEOUT: 20,
            CONF_VERIFY_SSL: False,
            CONF_MAX_RESPONSE_SIZE: 0,
            CONF_RETRIES: 3,
            CONF_RETRY_DELAY: 5,
        },
    )
    assert result4["type"] == FlowResultType.FORM
    assert result4["step_id"] == "edit_endpoint_auth"

    result5 = await hass.config_entries.options.async_configure(
        result4["flow_id"],
        {
            CONF_AUTH_TYPE: "none",
        },
    )
    assert result5["type"] == FlowResultType.CREATE_ENTRY

    endpoints = result5["data"][CONF_ENDPOINTS]
    assert len(endpoints) == 1
    assert endpoints[0][CONF_ENDPOINT_NAME] == "Updated Test Endpoint"
    assert endpoints[0][CONF_URL] == "https://api.example.com/updated"
    assert endpoints[0][CONF_METHOD] == "PUT"
    assert endpoints[0][CONF_TIMEOUT] == 20
    assert endpoints[0][CONF_VERIFY_SSL] is False
    assert endpoints[0][CONF_MAX_RESPONSE_SIZE] == 0
    assert endpoints[0][CONF_RETRIES] == 3
    assert endpoints[0][CONF_RETRY_DELAY] == 5


async def test_options_remove_endpoint(hass: HomeAssistant, mock_config_entry_data, mock_endpoint_config) -> None:
    """Test removing an endpoint through options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data,
        options={CONF_ENDPOINTS: [mock_endpoint_config]},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"next_step_id": "remove_endpoint"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "remove_endpoint"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {"endpoint": mock_endpoint_config[CONF_ENDPOINT_ID]},
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY

    endpoints = result3["data"][CONF_ENDPOINTS]
    assert len(endpoints) == 0
