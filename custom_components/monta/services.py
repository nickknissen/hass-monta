"""Monta components services.

The services are registered once for the whole integration, not once per
config entry: registration is keyed by (domain, service), so a per-entry
registration would silently replace the previous entry's handler. The entry
that owns a charge point is therefore resolved per call instead of being
captured at registration time.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .coordinator import MontaChargePointCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_START_CHARGING = "start_charging"
SERVICE_STOP_CHARGING = "stop_charging"

# The UI picker hands over a Home Assistant device id, while automations pass
# the numeric Monta charge point id. Both are accepted and normalised by
# _resolve_charge_point_id.
has_id_schema = vol.Schema(
    {vol.Required("charge_point_id"): vol.Any(vol.Coerce(int), str)},
)


def _resolve_charge_point_id(hass: HomeAssistant, value: int | str) -> int:
    """Return the Monta charge point id for a service call field value.

    The field accepts the numeric charge point id, as used by existing
    automations, or the device id the UI service picker sends.
    """
    if isinstance(value, int):
        return value

    device = dr.async_get(hass).async_get(value)
    if device is None:
        msg = f"Device {value} not found"
        raise HomeAssistantError(msg)

    for domain, identifier in device.identifiers:
        if domain == DOMAIN and identifier.isdigit():
            return int(identifier)

    msg = f"Device {device.name or value} is not a Monta charge point"
    raise HomeAssistantError(msg)


def _resolve_coordinator(
    hass: HomeAssistant,
    charge_point_id: int,
) -> MontaChargePointCoordinator:
    """Return the coordinator of the entry that owns this charge point."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        coordinator = entry_data["charge_point"]
        if coordinator.data and charge_point_id in coordinator.data:
            return coordinator

    msg = f"Charge point {charge_point_id} not found"
    raise HomeAssistantError(msg)


def _state_error_message(
    action: str,
    charge_point_state: str,
    expected_state: str,
) -> HomeAssistantError:
    msg = (
        f"Cannot {action} charging. "
        f"Charger is in state '{charge_point_state}'. Expected: {expected_state}"
    )
    return HomeAssistantError(msg)


async def _service_handle_start_charging(service_call: ServiceCall) -> None:
    """Handle the start charging service call."""
    charge_point_id = _resolve_charge_point_id(
        service_call.hass, service_call.data["charge_point_id"],
    )
    _LOGGER.debug("Called start charging for %s", charge_point_id)

    coordinator = _resolve_coordinator(service_call.hass, charge_point_id)

    charge_point_state = coordinator.data[charge_point_id].state
    if charge_point_state != "available":
        raise _state_error_message("start", charge_point_state, "available")

    await coordinator.async_start_charge(charge_point_id)
    _LOGGER.info(
        "Successfully started charging for charge point %s",
        charge_point_id,
    )


async def _service_handle_stop_charging(service_call: ServiceCall) -> None:
    """Handle the stop charging service call."""
    charge_point_id = _resolve_charge_point_id(
        service_call.hass, service_call.data["charge_point_id"],
    )
    _LOGGER.debug("Called stop charging for %s", charge_point_id)

    coordinator = _resolve_coordinator(service_call.hass, charge_point_id)

    charge_point_state = coordinator.data[charge_point_id].state
    if not charge_point_state.startswith("busy"):
        raise _state_error_message("stop", charge_point_state, "busy")

    await coordinator.async_stop_charge(charge_point_id)
    _LOGGER.info(
        "Successfully stopped charging for charge point %s",
        charge_point_id,
    )


# LIST OF SERVICES
SERVICES: list[tuple[str, vol.Schema, Any]] = [
    (SERVICE_START_CHARGING, has_id_schema, _service_handle_start_charging),
    (SERVICE_STOP_CHARGING, has_id_schema, _service_handle_stop_charging),
]


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Monta services, once for all config entries."""
    if hass.services.has_service(DOMAIN, SERVICE_START_CHARGING):
        return

    _LOGGER.debug("Set up services")
    for name, schema, handler in SERVICES:
        hass.services.async_register(DOMAIN, name, handler, schema=schema)


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the Monta services, once the last config entry is unloaded."""
    _LOGGER.debug("Remove services")
    for name, _schema, _handler in SERVICES:
        hass.services.async_remove(DOMAIN, name)
