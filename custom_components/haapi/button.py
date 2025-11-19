"""Button platform for HAAPI integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_ENDPOINT_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAPI button from a config entry."""
    api_caller = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([HaapiButton(api_caller, entry)], True)


class HaapiButton(ButtonEntity):
    """Representation of a HAAPI button."""

    def __init__(self, api_caller, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._api_caller = api_caller
        self._entry = entry
        endpoint_name = entry.data[CONF_ENDPOINT_NAME]

        self._attr_name = "Trigger"
        self._attr_unique_id = f"{entry.entry_id}_trigger"
        self._attr_has_entity_name = True

        # Device info for grouping entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=endpoint_name,
            manufacturer="HAAPI",
            model="API Endpoint",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Button pressed for %s", self._entry.data[CONF_ENDPOINT_NAME])
        await self._api_caller.async_call_api()
