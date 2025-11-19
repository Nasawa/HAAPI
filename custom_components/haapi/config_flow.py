"""Config flow for HAAPI integration."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector, entity_registry as er, device_registry as dr
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_ENDPOINTS,
    CONF_ENDPOINT_ID,
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
)

_LOGGER = logging.getLogger(__name__)


class HaapiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAAPI."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._endpoint_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - create HAAPI integration."""
        if user_input is not None:
            # Create entry with user-provided name
            title = user_input.get("name", "HAAPI")
            return self.async_create_entry(
                title=title,
                data={},
                options={CONF_ENDPOINTS: []},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("name", default="HAAPI"): cv.string,
            }),
            description_placeholders={
                "info": "Create a HAAPI integration instance to manage REST API endpoints."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HaapiOptionsFlowHandler:
        """Get the options flow for this handler."""
        return HaapiOptionsFlowHandler(config_entry)


class HaapiOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for HAAPI."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._endpoint_data: dict[str, Any] = {}
        self._endpoint_id: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage endpoints."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_endpoint", "edit_endpoint", "remove_endpoint"],
        )

    async def async_step_add_endpoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new endpoint."""
        if user_input is not None:
            self._endpoint_data = user_input.copy()
            return await self.async_step_add_endpoint_auth()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ENDPOINT_NAME): cv.string,
                vol.Required(CONF_URL): cv.string,
                vol.Required(CONF_METHOD, default=DEFAULT_METHOD): vol.In(HTTP_METHODS),
                vol.Optional(CONF_HEADERS, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_BODY, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): cv.string,
            }
        )

        return self.async_show_form(
            step_id="add_endpoint",
            data_schema=data_schema,
        )

    async def async_step_add_endpoint_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure authentication for new endpoint."""
        if user_input is not None:
            self._endpoint_data.update(user_input)

            # Generate unique ID for this endpoint
            endpoint_id = str(uuid.uuid4())
            self._endpoint_data[CONF_ENDPOINT_ID] = endpoint_id

            # Add endpoint to options
            endpoints = self.config_entry.options.get(CONF_ENDPOINTS, []).copy()
            endpoints.append(self._endpoint_data)

            return self.async_create_entry(
                title="",
                data={CONF_ENDPOINTS: endpoints},
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_AUTH_TYPE, default=DEFAULT_AUTH_TYPE): vol.In(AUTH_TYPES),
                vol.Optional(CONF_USERNAME, default=""): cv.string,
                vol.Optional(CONF_PASSWORD, default=""): cv.string,
                vol.Optional(CONF_BEARER_TOKEN, default=""): cv.string,
                vol.Optional(CONF_API_KEY, default=""): cv.string,
            }
        )

        return self.async_show_form(
            step_id="add_endpoint_auth",
            data_schema=data_schema,
            description_placeholders={
                "endpoint_name": self._endpoint_data[CONF_ENDPOINT_NAME]
            },
        )

    async def async_step_edit_endpoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select endpoint to edit."""
        endpoints = self.config_entry.options.get(CONF_ENDPOINTS, [])

        if not endpoints:
            return self.async_abort(reason="no_endpoints")

        if user_input is not None:
            self._endpoint_id = user_input["endpoint"]
            # Find the endpoint
            for endpoint in endpoints:
                if endpoint[CONF_ENDPOINT_ID] == self._endpoint_id:
                    self._endpoint_data = endpoint.copy()
                    break
            return await self.async_step_edit_endpoint_config()

        # Create selection options
        endpoint_options = {
            ep[CONF_ENDPOINT_ID]: ep[CONF_ENDPOINT_NAME]
            for ep in endpoints
        }

        data_schema = vol.Schema(
            {
                vol.Required("endpoint"): vol.In(endpoint_options),
            }
        )

        return self.async_show_form(
            step_id="edit_endpoint",
            data_schema=data_schema,
        )

    async def async_step_edit_endpoint_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit endpoint configuration."""
        if user_input is not None:
            self._endpoint_data.update(user_input)
            return await self.async_step_edit_endpoint_auth()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENDPOINT_NAME,
                    default=self._endpoint_data.get(CONF_ENDPOINT_NAME)
                ): cv.string,
                vol.Required(
                    CONF_URL,
                    default=self._endpoint_data.get(CONF_URL)
                ): cv.string,
                vol.Required(
                    CONF_METHOD,
                    default=self._endpoint_data.get(CONF_METHOD, DEFAULT_METHOD)
                ): vol.In(HTTP_METHODS),
                vol.Optional(
                    CONF_HEADERS,
                    default=self._endpoint_data.get(CONF_HEADERS, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(
                    CONF_BODY,
                    default=self._endpoint_data.get(CONF_BODY, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=True,
                        type=selector.TextSelectorType.TEXT,
                    )
                ),
                vol.Optional(
                    CONF_CONTENT_TYPE,
                    default=self._endpoint_data.get(CONF_CONTENT_TYPE, DEFAULT_CONTENT_TYPE)
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="edit_endpoint_config",
            data_schema=data_schema,
        )

    async def async_step_edit_endpoint_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit endpoint authentication."""
        if user_input is not None:
            self._endpoint_data.update(user_input)

            # Update the endpoint in options
            endpoints = self.config_entry.options.get(CONF_ENDPOINTS, []).copy()
            for i, endpoint in enumerate(endpoints):
                if endpoint[CONF_ENDPOINT_ID] == self._endpoint_id:
                    endpoints[i] = self._endpoint_data
                    break

            return self.async_create_entry(
                title="",
                data={CONF_ENDPOINTS: endpoints},
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_AUTH_TYPE,
                    default=self._endpoint_data.get(CONF_AUTH_TYPE, DEFAULT_AUTH_TYPE)
                ): vol.In(AUTH_TYPES),
                vol.Optional(
                    CONF_USERNAME,
                    default=self._endpoint_data.get(CONF_USERNAME, "")
                ): cv.string,
                vol.Optional(
                    CONF_PASSWORD,
                    default=self._endpoint_data.get(CONF_PASSWORD, "")
                ): cv.string,
                vol.Optional(
                    CONF_BEARER_TOKEN,
                    default=self._endpoint_data.get(CONF_BEARER_TOKEN, "")
                ): cv.string,
                vol.Optional(
                    CONF_API_KEY,
                    default=self._endpoint_data.get(CONF_API_KEY, "")
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="edit_endpoint_auth",
            data_schema=data_schema,
            description_placeholders={
                "endpoint_name": self._endpoint_data[CONF_ENDPOINT_NAME]
            },
        )

    async def async_step_remove_endpoint(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove an endpoint."""
        endpoints = self.config_entry.options.get(CONF_ENDPOINTS, [])

        if not endpoints:
            return self.async_abort(reason="no_endpoints")

        if user_input is not None:
            endpoint_id_to_remove = user_input["endpoint"]

            # Remove all entities associated with this endpoint
            entity_registry = er.async_get(self.hass)
            entries = er.async_entries_for_config_entry(
                entity_registry, self.config_entry.entry_id
            )

            # Find and remove entities for this endpoint
            for entity_entry in entries:
                if endpoint_id_to_remove in entity_entry.unique_id:
                    entity_registry.async_remove(entity_entry.entity_id)
                    _LOGGER.debug(
                        "Removed entity %s for endpoint %s",
                        entity_entry.entity_id,
                        endpoint_id_to_remove,
                    )

            # Remove the device associated with this endpoint
            device_registry = dr.async_get(self.hass)
            device_identifier = (DOMAIN, f"{self.config_entry.entry_id}_{endpoint_id_to_remove}")
            device_entry = device_registry.async_get_device(identifiers={device_identifier})

            if device_entry:
                device_registry.async_remove_device(device_entry.id)
                _LOGGER.debug(
                    "Removed device for endpoint %s",
                    endpoint_id_to_remove,
                )

            # Remove the endpoint from options
            endpoints = [
                ep for ep in endpoints
                if ep[CONF_ENDPOINT_ID] != endpoint_id_to_remove
            ]

            return self.async_create_entry(
                title="",
                data={CONF_ENDPOINTS: endpoints},
            )

        # Create selection options
        endpoint_options = {
            ep[CONF_ENDPOINT_ID]: ep[CONF_ENDPOINT_NAME]
            for ep in endpoints
        }

        data_schema = vol.Schema(
            {
                vol.Required("endpoint"): vol.In(endpoint_options),
            }
        )

        return self.async_show_form(
            step_id="remove_endpoint",
            data_schema=data_schema,
        )
