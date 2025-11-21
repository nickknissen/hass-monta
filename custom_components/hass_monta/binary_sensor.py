"""Binary sensor platform for monta."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import generate_entity_id

from .const import DOMAIN
from .entity import MontaEntity
from .utils import snake_case

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MontaChargePointCoordinator

_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="cable_plugged_in",
        name="Cable Plugged In",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    charge_point_coordinator = coordinators["charge_point"]

    for charge_point_id in charge_point_coordinator.data:
        async_add_devices(
            [
                MontaBinarySensor(
                    coordinator=charge_point_coordinator,
                    entity_description=entity_description,
                    charge_point_id=charge_point_id,
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ],
        )


class MontaBinarySensor(MontaEntity, BinarySensorEntity):
    """monta binary_sensor class."""

    def __init__(
        self,
        coordinator: MontaChargePointCoordinator,
        entity_description: BinarySensorEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator, charge_point_id)

        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{charge_point_id}_{snake_case(entity_description.key)}",
            [str(charge_point_id)],
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        charge_point = self.coordinator.data[self.charge_point_id]
        # Get the attribute by name from the ChargePoint DTO
        return getattr(charge_point, self.entity_description.key, False)
