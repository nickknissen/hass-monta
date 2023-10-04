"""Sensor platform for monta."""
from __future__ import annotations
import logging

from attr import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)

from .const import DOMAIN, ChargerStatus
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity
from .utils import snake_case

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
    SensorEntityDescription(
        key="charger_lastMeterReadingKwh",
        name="Last meter reading",
        icon="mdi:counter",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for charge_point_id, _ in coordinator.data.items():
        async_add_entities(
            [
                MontaSensor(
                    coordinator,
                    entry,
                    description,
                    charge_point_id,
                )
                for description in ENTITY_DESCRIPTIONS
            ]
        )


class MontaSensor(MontaEntity, SensorEntity):
    """monta Sensor class."""

    def __init__(
        self,
        coordinator: MontaDataUpdateCoordinator,
        _: ConfigEntry,
        entity_description: SensorEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, charge_point_id)

        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{charge_point_id}_{snake_case(entity_description.key)}",
            [charge_point_id],
        )

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        _, data_key = self.entity_description.key.split("charger_")

        return self.coordinator.data[self.charge_point_id].get(data_key)
