"""Sensor platform for monta."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dateutil import parser
from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, ChargerStatus
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity
from .utils import snake_case

_LOGGER = logging.getLogger(__name__)


@dataclass
class MontaSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[Any], StateType]
    extra_state_attributes_fn: Callable[[Any], dict[str, str]] | None


@dataclass
class MontaSensorEntityDescription(
    SensorEntityDescription, MontaSensorEntityDescriptionMixin
):
    """Describes MontaSensor sensor entity."""


def last_charge_state(data: dict[str, Any]) -> str:
    """Process state for last charge (if available)."""
    return data["charges"][0]["state"] if len(data["charges"]) > 0 else None


def last_charge_extra_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Process extra attributes for last charge (if available)."""
    if len(data["charges"]) > 0:
        attributes = data["charges"][0]
        attributes["createdAt"] = _parse_date(attributes["createdAt"])
        attributes["updatedAt"] = _parse_date(attributes["updatedAt"])
        attributes["startedAt"] = _parse_date(attributes["startedAt"])
        attributes["stoppedAt"] = _parse_date(attributes["stoppedAt"])
        attributes["cablePluggedInAt"] = _parse_date(attributes["cablePluggedInAt"])
        attributes["fullyChargedAt"] = _parse_date(attributes["fullyChargedAt"])
        attributes["failedAt"] = _parse_date(attributes["failedAt"])
        attributes["timeoutAt"] = _parse_date(attributes["timeoutAt"])
        return attributes

    return None


def _parse_date(chargedate) -> str:
    return parser.parse(chargedate) if chargedate else None


ENTITY_DESCRIPTIONS: tuple[MontaSensorEntityDescription, ...] = (
    MontaSensorEntityDescription(
        key="charger_visibility",
        name="Visibility",
        icon="mdi:eye",
        device_class=SensorDeviceClass.ENUM,
        options=["public", "private"],
        value_fn=lambda data: data["visibility"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(
        key="charger_type",
        name="Type",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.ENUM,
        options=["ac", "dc"],
        value_fn=lambda data: data["type"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(
        key="charger_state",
        name="State",
        icon="mdi:state-machine",
        device_class=SensorDeviceClass.ENUM,
        options=[x.value for x in ChargerStatus],
        value_fn=lambda data: data["state"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(
        key="charger_lastMeterReadingKwh",
        name="Last meter reading",
        icon="mdi:counter",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        value_fn=lambda data: data["lastMeterReadingKwh"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(
        key="charge_startedAt",
        name="Last Charge",
        icon="mdi:ev-station",
        value_fn=last_charge_state,
        extra_state_attributes_fn=last_charge_extra_attributes,
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
    def native_value(self) -> StateType:
        """Return the state."""
        return self.entity_description.value_fn(
            self.coordinator.data[self.charge_point_id]
        )

    @property
    def extra_attributes(self) -> str:
        """Return extra attributes for trhe sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        if self.entity_description.extra_state_attributes_fn:
            return self.entity_description.extra_state_attributes_fn(
                self.coordinator.data[self.charge_point_id]
            )
        return None
