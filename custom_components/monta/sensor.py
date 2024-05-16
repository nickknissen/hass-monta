"""Sensor platform for monta."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CHARGEPOINTS,
    ATTR_WALLET,
    ATTRIBUTION,
    DOMAIN,
    WALLET_TIMEDELTA,
    ChargerStatus,
    WalletStatus,
)
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity
from .utils import snake_case

CHARGEPOINTDATEKEYS = [
    "createdAt",
    "updatedAt",
    "startedAt",
    "stoppedAt",
    "cablePluggedInAt",
    "fullyChargedAt",
    "failedAt",
    "timeoutAt",
]
WALLETDATEKEYS = [
    "createdAt",
    "updatedAt",
    "completedAt",
]


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


def _days_hours_minutes(td):
    return f"{td.days} days, {td.seconds//3600} hours, {(td.seconds//60)%60} minutes"


def last_charge_state(data: dict[str, Any]) -> str:
    """Process state for last charge (if available)."""
    return data["charges"][0]["state"] if len(data["charges"]) > 0 else None


def last_charge_extra_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Process extra attributes for last charge (if available)."""
    if data["charges"]:
        attributes = data["charges"][0]
        for key in CHARGEPOINTDATEKEYS:
            if key in attributes:
                attributes[key] = _parse_date(attributes[key])

        return attributes

    return None


def wallet_extra_attributes(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Process extra attributes for the wallet (if available)."""
    attributes = {"period_retrieved": _days_hours_minutes(WALLET_TIMEDELTA)}

    if data:
        for transaction in data:
            for key in WALLETDATEKEYS:
                if key in transaction:
                    transaction[key] = _parse_date(transaction[key])
        attributes["transactions"] = data

    return attributes


def _parse_date(chargedate: str):
    if isinstance(chargedate, str):
        return parser.parse(chargedate)

    if isinstance(chargedate, datetime):
        return chargedate

    return None


CHARGEPOINT_ENTITY_DESCRIPTIONS: tuple[MontaSensorEntityDescription, ...] = (
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_visibility",
        name="Visibility",
        icon="mdi:eye",
        device_class=SensorDeviceClass.ENUM,
        options=["public", "private"],
        value_fn=lambda data: data["visibility"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_type",
        name="Type",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.ENUM,
        options=["ac", "dc"],
        value_fn=lambda data: data["type"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_state",
        name="State",
        icon="mdi:state-machine",
        device_class=SensorDeviceClass.ENUM,
        options=[x.value for x in ChargerStatus],
        value_fn=lambda data: data["state"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_lastMeterReadingKwh",
        name="Last meter reading",
        icon="mdi:wallet",
        value_fn=lambda data: data["lastMeterReadingKwh"],
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charge_state",
        name="Last Charge",
        icon="mdi:ev-station",
        value_fn=last_charge_state,
        extra_state_attributes_fn=last_charge_extra_attributes,
    ),
)

WALLET_ENTITY_DESCRIPTIONS: tuple[MontaSensorEntityDescription, ...] = (
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="monta-personal-wallet",
        name="Monta - Personal Wallet",
        icon="mdi:eye",
        device_class=SensorDeviceClass.ENUM,
        options=[x.value for x in WalletStatus],
        value_fn=lambda data: data[0]["state"] if data else "none",
        extra_state_attributes_fn=wallet_extra_attributes,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for charge_point_id in coordinator.data[ATTR_CHARGEPOINTS].keys():
        async_add_entities(
            [
                MontaChargepointSensor(
                    coordinator,
                    entry,
                    description,
                    charge_point_id,
                )
                for description in CHARGEPOINT_ENTITY_DESCRIPTIONS
            ]
        )
    async_add_entities(
        [
            MontaWalletSensor(
                coordinator,
                entry,
                description,
            )
            for description in WALLET_ENTITY_DESCRIPTIONS
        ]
    )


class MontaChargepointSensor(MontaEntity, SensorEntity):
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
            self.coordinator.data[ATTR_CHARGEPOINTS][self.charge_point_id]
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
                self.coordinator.data[ATTR_CHARGEPOINTS][self.charge_point_id]
            )
        return None


class MontaWalletSensor(CoordinatorEntity[MontaDataUpdateCoordinator], SensorEntity):
    """monta Sensor class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MontaDataUpdateCoordinator,
        _: ConfigEntry,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"monta_{snake_case(entity_description.key)}",
            "personal_monta_wallet",
        )

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.data[ATTR_WALLET])

    @property
    def extra_attributes(self) -> str:
        """Return extra attributes for trhe sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        if self.entity_description.extra_state_attributes_fn:
            return self.entity_description.extra_state_attributes_fn(
                self.coordinator.data[ATTR_WALLET]
            )
        return None
