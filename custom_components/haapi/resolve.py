"""Resolve an automation/service target to HAAPI endpoint API callers."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)

from .const import DOMAIN


def endpoint_callers(hass: HomeAssistant, target: dict[str, Any] | None) -> list:
    """Return the HAAPI API callers for the endpoints referenced by a target.

    ``target`` is a dict with the usual target keys (device_id / entity_id /
    area_id / floor_id / label_id). HAAPI endpoints are devices, so any of those
    that resolve to a HAAPI endpoint device yield that endpoint's API caller.
    """
    if not target:
        return []
    selection = TargetSelection(target)
    if not selection.has_any_target:
        return []

    selected = async_extract_referenced_entity_ids(hass, selection)
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    device_ids: set[str] = set(selected.referenced_devices)
    for entity_id in selected.referenced | selected.indirectly_referenced:
        entry = ent_reg.async_get(entity_id)
        if entry and entry.device_id:
            device_ids.add(entry.device_id)

    domain_data = hass.data.get(DOMAIN, {})
    callers: list = []
    for device_id in device_ids:
        device = dev_reg.async_get(device_id)
        if not device:
            continue
        for domain, identifier in device.identifiers:
            if domain != DOMAIN:
                continue
            entry_id, _, endpoint_id = identifier.partition("_")
            coordinator = domain_data.get(entry_id)
            if coordinator is None:
                continue
            caller = coordinator.get_api_caller(endpoint_id)
            if caller is not None:
                callers.append(caller)
    return callers
