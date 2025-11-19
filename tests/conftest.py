"""Common fixtures for HAAPI tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.haapi.const import (
    CONF_API_KEY,
    CONF_AUTH_TYPE,
    CONF_BEARER_TOKEN,
    CONF_BODY,
    CONF_CONTENT_TYPE,
    CONF_ENDPOINT_ID,
    CONF_ENDPOINT_NAME,
    CONF_ENDPOINTS,
    CONF_HEADERS,
    CONF_MAX_RESPONSE_SIZE,
    CONF_METHOD,
    CONF_PASSWORD,
    CONF_RETRIES,
    CONF_RETRY_DELAY,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_USERNAME,
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


pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture
def mock_endpoint_config():
    """Return a mock endpoint configuration."""
    return {
        CONF_ENDPOINT_ID: "test-endpoint-id",
        CONF_ENDPOINT_NAME: "Test Endpoint",
        CONF_URL: "https://api.example.com/test",
        CONF_METHOD: DEFAULT_METHOD,
        CONF_HEADERS: "",
        CONF_BODY: "",
        CONF_CONTENT_TYPE: DEFAULT_CONTENT_TYPE,
        CONF_AUTH_TYPE: "none",
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
        CONF_VERIFY_SSL: DEFAULT_VERIFY_SSL,
        CONF_MAX_RESPONSE_SIZE: DEFAULT_MAX_RESPONSE_SIZE,
        CONF_RETRIES: DEFAULT_RETRIES,
        CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
    }


@pytest.fixture
def mock_config_entry_data():
    """Return mock config entry data."""
    return {CONF_NAME: "HAAPI Test"}


@pytest.fixture
def mock_config_entry_options(mock_endpoint_config):
    """Return mock config entry options."""
    return {CONF_ENDPOINTS: [mock_endpoint_config]}
