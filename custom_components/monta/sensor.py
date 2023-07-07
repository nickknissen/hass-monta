"""Sensor platform for monta."""
from __future__ import annotations
import logging

from attr import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)

from .const import DOMAIN, ChargerStatus
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class MontaSensorEntityDescription(SensorEntityDescription):
    """Describes a Monta sensor."""


ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="charger_visibility",
        name="Visibility",
        icon="mdi:eye",
        device_class=SensorDeviceClass.ENUM,
        options=["public", "private"],
    ),
    SensorEntityDescription(
        key="charger_type",
        name="Type",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.ENUM,
        options=["ac", "dc"],
    ),
    SensorEntityDescription(
        key="charger_state",
        name="State",
        icon="mdi:state-machine",
        device_class=SensorDeviceClass.ENUM,
        options=[x.value for x in ChargerStatus],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for charge_point_id, _ in coordinator.data.items():
        async_add_entities(
            MontaSensor(
                coordinator,
                entry,
                description,
                charge_point_id,
            )
            for description in ENTITY_DESCRIPTIONS
        )


class MontaSensor(MontaEntity, SensorEntity):
    """monta Sensor class."""

    def __init__(
        self,
        coordinator: MontaDataUpdateCoordinator,
        _: ConfigEntry,
        description: SensorEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, charge_point_id)

        self.entity_description = description
        self.entity_id = generate_entity_id(
            "sensor.{}", description.key, [charge_point_id]
        )
        self._attr_name = description.name
        self._attr_unique_id = f"{description.key}"

        self.charge_point_id = charge_point_id

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        _, data_key = self.entity_description.key.split("charger_")

        return self.coordinator.data[self.charge_point_id].get(data_key)
