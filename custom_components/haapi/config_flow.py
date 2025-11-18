"""Config flow for HAAPI integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_ENDPOINT_NAME,
    CONF_URL,
    CONF_METHOD,
    CONF_HEADERS,
    CONF_BODY,
    CONF_CONTENT_TYPE,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_BEARER_TOKEN,
    CONF_API_KEY,
    CONF_AUTH_TYPE,
    HTTP_METHODS,
    AUTH_TYPES,
    DEFAULT_METHOD,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_AUTH_TYPE,
    AUTH_NONE,
    AUTH_BASIC,
    AUTH_BEARER,
    AUTH_API_KEY,
)

_LOGGER = logging.getLogger(__name__)


class HaapiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAAPI."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store basic configuration
            self._data = user_input.copy()

            # Validate endpoint name is unique
            await self.async_set_unique_id(user_input[CONF_ENDPOINT_NAME])
            self._abort_if_unique_id_configured()

            # Move to authentication step
            return await self.async_step_auth()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ENDPOINT_NAME): cv.string,
                vol.Required(CONF_URL): cv.string,
                vol.Required(CONF_METHOD, default=DEFAULT_METHOD): vol.In(HTTP_METHODS),
                vol.Optional(CONF_HEADERS, default=""): cv.string,
                vol.Optional(CONF_BODY, default=""): cv.string,
                vol.Optional(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle authentication configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Merge authentication data with basic data
            self._data.update(user_input)

            # Create the config entry
            return self.async_create_entry(
                title=self._data[CONF_ENDPOINT_NAME],
                data=self._data,
            )

        # Build auth schema based on auth type
        auth_type = self._data.get(CONF_AUTH_TYPE, DEFAULT_AUTH_TYPE)

        data_schema = {
            vol.Required(CONF_AUTH_TYPE, default=DEFAULT_AUTH_TYPE): vol.In(AUTH_TYPES),
        }

        # Add conditional fields for authentication
        data_schema.update({
            vol.Optional(CONF_USERNAME): cv.string,
            vol.Optional(CONF_PASSWORD): cv.string,
            vol.Optional(CONF_BEARER_TOKEN): cv.string,
            vol.Optional(CONF_API_KEY): cv.string,
        })

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema(data_schema),
            errors=errors,
            description_placeholders={
                "endpoint_name": self._data[CONF_ENDPOINT_NAME]
            },
        )
