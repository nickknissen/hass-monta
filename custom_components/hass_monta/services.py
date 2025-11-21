"""Monta components services."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

has_id_schema = vol.Schema({vol.Required("charge_point_id"): int})


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for the Monta component."""
    _LOGGER.debug("Set up services")

    coordinators = hass.data[DOMAIN][entry.entry_id]
    charge_point_coordinator = coordinators["charge_point"]

    async def service_handle_stop_charging(service_call: ServiceCall) -> None:
        """Handle the stop charging service call."""
        charge_point_id = service_call.data["charge_point_id"]
        _LOGGER.debug("Called stop charging for %s", charge_point_id)

        # Check if charge point exists
        if charge_point_id not in charge_point_coordinator.data:
            msg = f"Charge point {charge_point_id} not found"
            raise HomeAssistantError(msg)

        charge_point_state = charge_point_coordinator.data[charge_point_id].state
        if charge_point_state.startswith("busy"):
            await charge_point_coordinator.async_stop_charge(charge_point_id)
            _LOGGER.info(
                "Successfully stopped charging for charge point %s",
                charge_point_id,
            )
            return

        action = "stop"
        raise state_error_message(
            action,
            charge_point_state,
            "busy",
        )

    async def service_handle_start_charging(service_call: ServiceCall) -> None:
        """Handle the start charging service call."""
        charge_point_id = service_call.data["charge_point_id"]
        _LOGGER.debug("Called start charging for %s", charge_point_id)

        # Check if charge point exists
        if charge_point_id not in charge_point_coordinator.data:
            msg = f"Charge point {charge_point_id} not found"
            raise HomeAssistantError(msg)

        charge_point_state = charge_point_coordinator.data[charge_point_id].state
        if charge_point_state == "available":
            await charge_point_coordinator.async_start_charge(charge_point_id)
            _LOGGER.info(
                "Successfully started charging for charge point %s",
                charge_point_id,
            )
            return

        action = "start"
        raise state_error_message(
            action,
            charge_point_state,
            "available",
        )

    def state_error_message(
        action: str,
        charge_point_state: str,
        expected_state: str,
    ) -> HomeAssistantError:
        msg = (
            f"Cannot {action} charging. "
            f"Charger is in state '{charge_point_state}'. Expected: {expected_state}"
        )
        return HomeAssistantError(msg)

    # LIST OF SERVICES
    services: list[tuple[str, vol.Schema, Any]] = [
        ("start_charging", has_id_schema, service_handle_start_charging),
        ("stop_charging", has_id_schema, service_handle_stop_charging),
    ]

    # Register the services
    for name, schema, handler in services:
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
