"""Sensor platform for HAAPI integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_ENDPOINT_ID,
    CONF_ENDPOINT_NAME,
    CONF_URL,
    CONF_METHOD,
    CONF_HEADERS,
    CONF_BODY,
    CONF_CONTENT_TYPE,
    CONF_TIMEOUT,
    ATTR_RESPONSE_BODY,
    ATTR_RESPONSE_HEADERS,
    ATTR_REQUEST_HEADERS,
    ATTR_REQUEST_BODY,
    ATTR_URL,
    ATTR_CONTENT_TYPE,
    ATTR_TIMEOUT,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAPI sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    for endpoint_config in coordinator.get_all_endpoints():
        endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
        api_caller = coordinator.get_api_caller(endpoint_id)
        if api_caller:
            sensors.extend([
                HaapiRequestSensor(api_caller, entry, endpoint_config),
                HaapiResponseSensor(api_caller, entry, endpoint_config),
            ])

    async_add_entities(sensors, True)


class HaapiBaseSensor(SensorEntity):
    """Base class for HAAPI sensors."""

    def __init__(self, api_caller, entry: ConfigEntry, endpoint_config: dict) -> None:
        """Initialize the sensor."""
        self._api_caller = api_caller
        self._entry = entry
        self._endpoint_config = endpoint_config
        endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
        endpoint_name = endpoint_config[CONF_ENDPOINT_NAME]

        # Device info for grouping entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{endpoint_id}")},
            name=endpoint_name,
            manufacturer="HAAPI",
            model="API Endpoint",
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to hass."""
        self._api_caller.add_listener(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle updated data from the API caller."""
        self.async_write_ha_state()


class HaapiRequestSensor(HaapiBaseSensor):
    """Sensor for API request configuration."""

    def __init__(self, api_caller, entry: ConfigEntry, endpoint_config: dict) -> None:
        """Initialize the request sensor."""
        super().__init__(api_caller, entry, endpoint_config)
        endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
        self._attr_name = "Request"
        self._attr_unique_id = f"{entry.entry_id}_{endpoint_id}_request"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:send"

    @property
    def native_value(self) -> str | None:
        """Return the HTTP method as state."""
        return self._endpoint_config[CONF_METHOD]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return request configuration as attributes."""
        attrs = {
            ATTR_URL: self._endpoint_config[CONF_URL],
        }

        # Add raw request headers (non-templated)
        if CONF_HEADERS in self._endpoint_config and self._endpoint_config[CONF_HEADERS]:
            attrs[ATTR_REQUEST_HEADERS] = self._endpoint_config[CONF_HEADERS]

        # Add raw request body (non-templated)
        if CONF_BODY in self._endpoint_config and self._endpoint_config[CONF_BODY]:
            attrs[ATTR_REQUEST_BODY] = self._endpoint_config[CONF_BODY]

        # Add content type
        if CONF_CONTENT_TYPE in self._endpoint_config and self._endpoint_config[CONF_CONTENT_TYPE]:
            attrs[ATTR_CONTENT_TYPE] = self._endpoint_config[CONF_CONTENT_TYPE]

        # Add timeout
        attrs[ATTR_TIMEOUT] = self._endpoint_config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        return attrs


class HaapiResponseSensor(HaapiBaseSensor):
    """Sensor for API response."""

    def __init__(self, api_caller, entry: ConfigEntry, endpoint_config: dict) -> None:
        """Initialize the response sensor."""
        super().__init__(api_caller, entry, endpoint_config)
        endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
        self._attr_name = "Response"
        self._attr_unique_id = f"{entry.entry_id}_{endpoint_id}_response"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:receipt-text"

    @property
    def native_value(self) -> int | None:
        """Return the HTTP status code as state."""
        return self._api_caller.last_response_code

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return response data as attributes."""
        attrs = {}

        if self._api_caller.last_response_body is not None:
            attrs[ATTR_RESPONSE_BODY] = self._api_caller.last_response_body

        if self._api_caller.last_response_headers is not None:
            attrs[ATTR_RESPONSE_HEADERS] = self._api_caller.last_response_headers

        return attrs
