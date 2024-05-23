"""Monta components services."""

import logging
from collections.abc import Awaitable, Callable

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import ATTR_CHARGE_POINTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

TServiceHandler = Callable[[ServiceCall], Awaitable[None]]

has_id_schema = vol.Schema({vol.Required("charge_point_id"): int})


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for the Monta component."""

    _LOGGER.debug("Set up services")

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async def service_handle_stop_charging(service_call: ServiceCall) -> None:
        charge_point_id = service_call.data["charge_point_id"]
        _LOGGER.debug("Called stop charging for %s", charge_point_id)

        if coordinator.data[ATTR_CHARGE_POINTS][charge_point_id]["state"].startswith(
            "busy"
        ):
            await coordinator.async_stop_charge(charge_point_id)
            return

        raise vol.Invalid("Charger not currently charging")

    async def service_handle_start_charging(service_call: ServiceCall) -> None:
        charge_point_id = service_call.data["charge_point_id"]
        _LOGGER.debug("Called start charging for %s", charge_point_id)

        if coordinator.data[ATTR_CHARGE_POINTS][charge_point_id]["state"] == "available":
            await coordinator.async_start_charge(charge_point_id)
            return

        raise vol.Invalid("Charger not currently charging")

    # LIST OF SERVICES
    services: list[tuple[str, vol.Schema, TServiceHandler]] = [
        ("start_charging", has_id_schema, service_handle_start_charging),
        ("stop_charging", has_id_schema, service_handle_stop_charging),
    ]

    # Register the services
    for name, schema, handler in services:
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
