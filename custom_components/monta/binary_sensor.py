"""Binary sensor platform for monta."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import generate_entity_id

from .const import ATTR_CHARGE_POINTS, DOMAIN
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

    for charge_point_id in coordinator.data[ATTR_CHARGE_POINTS]:
        async_add_devices(
            [
                MontaBinarySensor(
                    coordinator=coordinator,
                    entity_description=entity_description,
                    charge_point_id=charge_point_id,
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ]
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
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{charge_point_id}_{snake_case(entity_description.key)}",
            [charge_point_id],
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data[ATTR_CHARGE_POINTS][self.charge_point_id].get(
            self.entity_description.key, False
        )
