"""Condition platform for the HAAPI integration.

Integration-specific conditions (Home Assistant 2026.7+) so automations can gate
on the result of an endpoint's most recent call without templating. Each
condition is evaluated against the live stored response for the targeted
endpoint device(s); with multiple targets, all must satisfy the condition.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.const import CONF_OPTIONS, CONF_TARGET
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.condition import Condition
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from .const import CONF_EQUALS, CONF_PATH, CONF_PATTERN
from .matching import UNSET, resolve_path, valid_regex, value_text
from .resolve import endpoint_callers

if TYPE_CHECKING:
    from homeassistant.helpers.condition import ConditionChecker, ConditionConfig

_BASE_CONDITION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default={}): {},
    }
)

_RESPONSE_CONTAINS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS): {
            vol.Required(CONF_PATTERN): vol.All(cv.string, valid_regex),
        },
    }
)

_VALUE_IS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS): {
            vol.Required(CONF_PATH): cv.string,
            vol.Optional(CONF_EQUALS): cv.string,
            vol.Optional(CONF_PATTERN): vol.All(cv.string, valid_regex),
        },
    }
)


class HaapiCondition(Condition):
    """Base class for HAAPI conditions evaluated against the last response.

    Subclasses define ``_predicate`` against a single endpoint's API caller; the
    condition is true when every targeted endpoint satisfies it.
    """

    _schema: vol.Schema = _BASE_CONDITION_SCHEMA

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the condition config."""
        return cls._schema(config)

    def __init__(self, hass: HomeAssistant, config: ConditionConfig) -> None:
        """Initialize the condition."""
        super().__init__(hass, config)
        self._target = config.target
        self._options = config.options or {}

    def _predicate(self, caller) -> bool:
        """Return whether a single endpoint's last response satisfies this."""
        raise NotImplementedError

    async def async_get_checker(self) -> ConditionChecker:
        """Return a checker that evaluates the condition against live state."""

        @callback
        def _check(hass: HomeAssistant, variables: TemplateVarsType) -> bool:
            callers = endpoint_callers(self._hass, self._target)
            if not callers:
                return False
            return all(self._predicate(caller) for caller in callers)

        return _check


class LastCallSucceededCondition(HaapiCondition):
    """True when the endpoint's last call returned a 2xx status."""

    def _predicate(self, caller) -> bool:
        code = caller.last_response_code
        return code is not None and 200 <= code < 300


class ResponseContainsCondition(HaapiCondition):
    """True when the endpoint's last response body matches a regex."""

    _schema = _RESPONSE_CONTAINS_SCHEMA

    def _predicate(self, caller) -> bool:
        body = caller.last_response_body
        if body is None:
            return False
        return re.search(self._options[CONF_PATTERN], body) is not None


class ValueIsCondition(HaapiCondition):
    """True when a JSON field in the last response equals / matches a value."""

    _schema = _VALUE_IS_SCHEMA

    def _predicate(self, caller) -> bool:
        value = resolve_path(caller.last_response_body, self._options[CONF_PATH])
        if value is UNSET:
            return False
        equals = self._options.get(CONF_EQUALS)
        pattern = self._options.get(CONF_PATTERN)
        if equals is None and pattern is None:
            return True
        text = value_text(value)
        if equals is not None and text != str(equals):
            return False
        if pattern is not None and re.search(pattern, text) is None:
            return False
        return True


CONDITIONS: dict[str, type[Condition]] = {
    "last_call_succeeded": LastCallSucceededCondition,
    "response_contains": ResponseContainsCondition,
    "value_is": ValueIsCondition,
}


async def async_get_conditions(hass: HomeAssistant) -> dict[str, type[Condition]]:
    """Return the conditions provided by HAAPI."""
    return CONDITIONS
