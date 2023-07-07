"""Binary sensor platform for monta."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import DOMAIN

from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity

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

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data[self.charge_point_id].get("cablePluggedIn", False)
