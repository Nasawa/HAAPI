"""Trigger platform for the HAAPI integration.

Exposes integration-specific triggers (Home Assistant 2026.7+) so automations
can react to an endpoint completing a call without watching the response sensor
with a generic state trigger -- which silently misses repeats when the status
code does not change. Each trigger listens for the ``haapi_response`` event the
integration fires on every completed call.
"""

from __future__ import annotations

import json
import re
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
    ATTR_BODY,
    ATTR_BODY_CHANGED,
    ATTR_ENDPOINT_ID,
    ATTR_ENDPOINT_NAME,
    ATTR_ENTRY_ID,
    ATTR_OK,
    ATTR_PREVIOUS_BODY,
    ATTR_PREVIOUS_STATUS,
    ATTR_STATUS,
    ATTR_STATUS_CHANGED,
    CONF_EQUALS,
    CONF_PATH,
    CONF_PATTERN,
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
        ATTR_BODY,
        ATTR_PREVIOUS_STATUS,
        ATTR_PREVIOUS_BODY,
    }
)

# Sentinel for "path not resolvable" (distinct from a real None value).
_UNSET = object()


def _resolve_path(body: str | None, path: str) -> Any:
    """Resolve a dotted path (e.g. ``state`` or ``ams.0.humidity``) in a JSON body.

    Returns the value at the path, or ``_UNSET`` if the body is not JSON or the
    path does not resolve. List indices are written as integers in the path.
    """
    if body is None:
        return _UNSET
    try:
        current = json.loads(body)
    except (ValueError, TypeError):
        return _UNSET
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return _UNSET
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return _UNSET
            if not -len(current) <= index < len(current):
                return _UNSET
            current = current[index]
        else:
            return _UNSET
    return current


def _valid_regex(value: str) -> str:
    """Validate that a string compiles as a regex."""
    try:
        re.compile(value)
    except re.error as err:
        raise vol.Invalid(f"Invalid regular expression: {err}") from err
    return value

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

_BODY_MATCHES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS): {
            vol.Required(CONF_PATTERN): vol.All(cv.string, _valid_regex),
        },
    }
)

_VALUE_MATCHES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS): {
            vol.Required(CONF_PATH): cv.string,
            vol.Optional(CONF_EQUALS): cv.string,
            vol.Optional(CONF_PATTERN): vol.All(cv.string, _valid_regex),
        },
    }
)

_VALUE_CHANGED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS): {
            vol.Required(CONF_PATH): cv.string,
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


class BodyMatchesTrigger(HaapiTrigger):
    """Fire when the response body matches a regular expression."""

    _schema = _BODY_MATCHES_SCHEMA

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        body = data[ATTR_BODY]
        if body is None:
            return False
        return re.search(self._options[CONF_PATTERN], body) is not None


class ValueMatchesTrigger(HaapiTrigger):
    """Fire when a JSON field in the body equals / matches a value.

    ``path`` is a dotted path (``state``, ``ams.0.humidity``). With ``equals``
    the field must equal that value (string comparison); with ``pattern`` the
    field must match that regex. With neither, fires whenever the path resolves.
    """

    _schema = _VALUE_MATCHES_SCHEMA

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        value = _resolve_path(data[ATTR_BODY], self._options[CONF_PATH])
        if value is _UNSET:
            return False
        equals = self._options.get(CONF_EQUALS)
        pattern = self._options.get(CONF_PATTERN)
        if equals is None and pattern is None:
            return True
        text = (
            json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        )
        if equals is not None and text != str(equals):
            return False
        if pattern is not None and re.search(pattern, text) is None:
            return False
        return True


class ValueChangedTrigger(HaapiTrigger):
    """Fire when a JSON field in the body changes from the previous call."""

    _schema = _VALUE_CHANGED_SCHEMA

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        path = self._options[CONF_PATH]
        current = _resolve_path(data[ATTR_BODY], path)
        if current is _UNSET:
            return False
        return current != _resolve_path(data[ATTR_PREVIOUS_BODY], path)


class RecoveredTrigger(HaapiTrigger):
    """Fire when a call succeeds (2xx) after the previous call had failed."""

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        if not data[ATTR_OK]:
            return False
        prev = data[ATTR_PREVIOUS_STATUS]
        return prev is not None and (prev == 0 or prev >= 400)


class WentDownTrigger(HaapiTrigger):
    """Fire when a call fails after the previous call had succeeded (2xx)."""

    @callback
    def _event_matches(self, data: dict[str, Any]) -> bool:
        status = data[ATTR_STATUS]
        if not (status == 0 or status >= 400):
            return False
        prev = data[ATTR_PREVIOUS_STATUS]
        return prev is not None and 200 <= prev < 300


TRIGGERS: dict[str, type[Trigger]] = {
    "response_received": ResponseReceivedTrigger,
    "call_succeeded": CallSucceededTrigger,
    "call_failed": CallFailedTrigger,
    "response_changed": ResponseChangedTrigger,
    "status_changed": StatusChangedTrigger,
    "body_matches": BodyMatchesTrigger,
    "value_matches": ValueMatchesTrigger,
    "value_changed": ValueChangedTrigger,
    "recovered": RecoveredTrigger,
    "went_down": WentDownTrigger,
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the triggers provided by HAAPI."""
    return TRIGGERS
