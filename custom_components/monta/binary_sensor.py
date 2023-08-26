"""Binary sensor platform for monta."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import generate_entity_id

from .const import DOMAIN
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity
from .utils import snake_case

_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="cablePluggedIn",
        name="Cable Plugged In",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for charge_point_id, _ in coordinator.data.items():
        async_add_devices(
            MontaBinarySensor(
                coordinator=coordinator,
                entity_description=entity_description,
                charge_point_id=charge_point_id,
            )
            for entity_description in ENTITY_DESCRIPTIONS
        )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("start_charge", {}, "start_charge")
    platform.async_register_entity_service("stop_charge", {}, "stop_charge")


class MontaBinarySensor(MontaEntity, BinarySensorEntity):
    """monta binary_sensor class."""

    def __init__(
        self,
        coordinator: MontaDataUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator, charge_point_id)

        self.entity_description = entity_description
        self.entity_id = generate_entity_id(
            "binary_sensor.{}", snake_case(entity_description.key), [charge_point_id]
        )
        self._attr_name = entity_description.name
        self._attr_unique_id = snake_case(entity_description.key)

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data[self.charge_point_id].get(
            self.entity_description.key, False
        )

    async def start_charge(self):
        """Start charge."""
        if (
            self.coordinator.data[self.charge_point_id]["state"] == "available"
            and self.coordinator.data[self.charge_point_id][self.entity_description.key]
        ):
            await self.coordinator.async_start_charge(self.charge_point_id)
            return

        raise vol.Invalid("Charger not plugged in and available for charge")

    async def stop_charge(self):
        """Stop charge."""
        if self.coordinator.data[self.charge_point_id]["state"].startswith("busy"):
            await self.coordinator.async_stop_charge(self.charge_point_id)
            return

        raise vol.Invalid("Charger not currently charging")
