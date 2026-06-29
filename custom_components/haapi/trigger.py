"""Trigger platform for the HAAPI integration.

Exposes integration-specific triggers (Home Assistant 2026.7+) so automations
can react to an endpoint completing a call without watching the response sensor
with a generic state trigger -- which silently misses repeats when the status
code does not change. Each trigger listens for the ``haapi_response`` event the
integration fires on every completed call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.const import CONF_OPTIONS, CONF_TARGET
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.helpers.trigger import Trigger
from homeassistant.helpers.typing import ConfigType

if TYPE_CHECKING:
    from homeassistant.helpers.trigger import (
        TriggerActionRunner,
        TriggerConfig,
        TriggerNotTriggeredReporter,
    )

from .const import (
    ATTR_BODY_CHANGED,
    ATTR_ENDPOINT_ID,
    ATTR_ENDPOINT_NAME,
    ATTR_ENTRY_ID,
    ATTR_OK,
    ATTR_STATUS,
    ATTR_STATUS_CHANGED,
    CONF_STATUS,
    DOMAIN,
    EVENT_HAAPI_RESPONSE,
)

# Keys every subclass reads off the event payload; used to drop malformed
# haapi_response events fired by foreign automations on the global bus.
_REQUIRED_EVENT_KEYS = frozenset(
    {
        ATTR_ENTRY_ID,
        ATTR_ENDPOINT_ID,
        ATTR_ENDPOINT_NAME,
        ATTR_STATUS,
        ATTR_OK,
        ATTR_STATUS_CHANGED,
        ATTR_BODY_CHANGED,
    }
)

_BASE_TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default={}): {},
    }
)

_RESPONSE_RECEIVED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default={}): {
            vol.Optional(CONF_STATUS): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=599)
            ),
        },
    }
)


class HaapiTrigger(Trigger):
    """Base class for HAAPI response triggers.

    Subclasses define ``_event_matches`` to decide which completed calls fire.
    An optional target restricts the trigger to specific endpoint devices; with
    no target it fires for every endpoint.
    """

    _schema: vol.Schema = _BASE_TRIGGER_SCHEMA

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the trigger config."""
        return cls._schema(config)

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        """Initialize the trigger."""
        super().__init__(hass, config)
        self._key = config.key
        self._target = config.target
        self._options = config.options or {}

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        """Return whether a completed call should fire this trigger."""
        return True

    @callback
    def _resolve_target_idents(self) -> set[str] | None:
        """Resolve the configured target to HAAPI device identifiers.

        Returns a set of ``"<entry_id>_<endpoint_id>"`` identifier strings, or
        ``None`` when no target is set (fire for every endpoint).
        """
        if not self._target:
            return None
        selection = TargetSelection(self._target)
        if not selection.has_any_target:
            return None

        selected = async_extract_referenced_entity_ids(self._hass, selection)
        ent_reg = er.async_get(self._hass)
        dev_reg = dr.async_get(self._hass)

        device_ids: set[str] = set(selected.referenced_devices)
        for entity_id in selected.referenced | selected.indirectly_referenced:
            entry = ent_reg.async_get(entity_id)
            if entry and entry.device_id:
                device_ids.add(entry.device_id)

        idents: set[str] = set()
        for device_id in device_ids:
            device = dev_reg.async_get(device_id)
            if not device:
                continue
            for domain, identifier in device.identifiers:
                if domain == DOMAIN:
                    idents.add(identifier)
        return idents or None

    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None = None,
    ) -> CALLBACK_TYPE:
        """Attach the trigger to its action runner."""
        allowed = self._resolve_target_idents()

        @callback
        def _handle_event(event: Event) -> None:
            data = event.data
            # The event bus is global, so a foreign automation could fire a
            # malformed haapi_response. Ignore anything missing required fields
            # instead of raising KeyError / spamming the log.
            if not _REQUIRED_EVENT_KEYS <= data.keys():
                return
            if allowed is not None:
                ident = f"{data[ATTR_ENTRY_ID]}_{data[ATTR_ENDPOINT_ID]}"
                if ident not in allowed:
                    return
            if not self._event_matches(data):
                return
            payload: dict[str, Any] = {"platform": self._key, **data}
            run_action(payload, f"{data[ATTR_ENDPOINT_NAME]} {self._key}", event.context)

        return self._hass.bus.async_listen(EVENT_HAAPI_RESPONSE, _handle_event)


class ResponseReceivedTrigger(HaapiTrigger):
    """Fire whenever an endpoint completes a call (any status)."""

    _schema = _RESPONSE_RECEIVED_SCHEMA

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        status = self._options.get(CONF_STATUS)
        return status is None or data[ATTR_STATUS] == status


class CallSucceededTrigger(HaapiTrigger):
    """Fire when an endpoint completes with a 2xx status."""

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        return bool(data[ATTR_OK])


class CallFailedTrigger(HaapiTrigger):
    """Fire when a call fails: network/timeout error (status 0) or HTTP >= 400."""

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        status = data[ATTR_STATUS]
        return status == 0 or status >= 400


class ResponseChangedTrigger(HaapiTrigger):
    """Fire when the response body differs from the previous call."""

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        return bool(data[ATTR_BODY_CHANGED])


class StatusChangedTrigger(HaapiTrigger):
    """Fire when the HTTP status code differs from the previous call."""

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        return bool(data[ATTR_STATUS_CHANGED])


TRIGGERS: dict[str, type[Trigger]] = {
    "response_received": ResponseReceivedTrigger,
    "call_succeeded": CallSucceededTrigger,
    "call_failed": CallFailedTrigger,
    "response_changed": ResponseChangedTrigger,
    "status_changed": StatusChangedTrigger,
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the triggers provided by HAAPI."""
    return TRIGGERS
