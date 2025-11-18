"""Sensor platform for HAAPI integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_ENDPOINT_NAME,
    CONF_URL,
    CONF_METHOD,
    ATTR_RESPONSE_BODY,
    ATTR_RESPONSE_HEADERS,
    ATTR_URL,
    ATTR_METHOD,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAPI sensors from a config entry."""
    api_caller = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        HaapiResponseCodeSensor(api_caller, entry),
        HaapiFetchTimeSensor(api_caller, entry),
        HaapiResponseBodySensor(api_caller, entry),
    ]

    async_add_entities(sensors, True)


class HaapiBaseSensor(SensorEntity):
    """Base class for HAAPI sensors."""

    def __init__(self, api_caller, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._api_caller = api_caller
        self._entry = entry
        self._endpoint_name = entry.data[CONF_ENDPOINT_NAME]

        # Device info for grouping entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=self._endpoint_name,
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


class HaapiResponseCodeSensor(HaapiBaseSensor):
    """Sensor for API response code."""

    def __init__(self, api_caller, entry: ConfigEntry) -> None:
        """Initialize the response code sensor."""
        super().__init__(api_caller, entry)
        self._attr_name = "Response Code"
        self._attr_unique_id = f"{entry.entry_id}_response_code"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:code-brackets"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self._api_caller.last_response_code

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            ATTR_URL: self._entry.data[CONF_URL],
            ATTR_METHOD: self._entry.data[CONF_METHOD],
        }


class HaapiFetchTimeSensor(HaapiBaseSensor):
    """Sensor for last fetch time."""

    def __init__(self, api_caller, entry: ConfigEntry) -> None:
        """Initialize the fetch time sensor."""
        super().__init__(api_caller, entry)
        self._attr_name = "Last Fetch Time"
        self._attr_unique_id = f"{entry.entry_id}_fetch_time"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        return self._api_caller.last_fetch_time


class HaapiResponseBodySensor(HaapiBaseSensor):
    """Sensor for API response body."""

    def __init__(self, api_caller, entry: ConfigEntry) -> None:
        """Initialize the response body sensor."""
        super().__init__(api_caller, entry)
        self._attr_name = "Response Body"
        self._attr_unique_id = f"{entry.entry_id}_response_body"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:file-document-outline"

    @property
    def native_value(self) -> datetime | None:
        """Return the fetch time as state (to avoid size limits)."""
        return self._api_caller.last_fetch_time

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the response body and headers as attributes."""
        attrs = {}

        if self._api_caller.last_response_body is not None:
            attrs[ATTR_RESPONSE_BODY] = self._api_caller.last_response_body

        if self._api_caller.last_response_headers is not None:
            attrs[ATTR_RESPONSE_HEADERS] = self._api_caller.last_response_headers

        return attrs
