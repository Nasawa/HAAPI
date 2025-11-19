"""Button platform for HAAPI integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_ENDPOINT_ID, CONF_ENDPOINT_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAAPI buttons from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create a button for each endpoint
    buttons = []
    for endpoint_config in coordinator.get_all_endpoints():
        endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
        api_caller = coordinator.get_api_caller(endpoint_id)
        if api_caller:
            buttons.append(HaapiButton(api_caller, entry, endpoint_config))

    async_add_entities(buttons, True)


class HaapiButton(ButtonEntity):
    """Representation of a HAAPI button."""

    def __init__(self, api_caller, entry: ConfigEntry, endpoint_config: dict) -> None:
        """Initialize the button."""
        self._api_caller = api_caller
        self._entry = entry
        self._endpoint_config = endpoint_config
        endpoint_id = endpoint_config[CONF_ENDPOINT_ID]
        endpoint_name = endpoint_config[CONF_ENDPOINT_NAME]

        self._attr_name = "Trigger"
        self._attr_unique_id = f"{entry.entry_id}_{endpoint_id}_trigger"
        self._attr_has_entity_name = True

        # Device info for grouping entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{endpoint_id}")},
            name=endpoint_name,
            manufacturer="HAAPI",
            model="API Endpoint",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Button pressed for %s", self._endpoint_config[CONF_ENDPOINT_NAME])
        await self._api_caller.async_call_api()
