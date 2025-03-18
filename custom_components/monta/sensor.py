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
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CHARGE_POINTS,
    ATTR_TRANSACTIONS,
    ATTR_WALLET,
    ATTRIBUTION,
    DOMAIN,
    ChargerStatus,
)
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity
from .utils import snake_case

CHARGE_POINT_DATE_KEYS = [
    "createdAt",
    "updatedAt",
    "startedAt",
    "stoppedAt",
    "cablePluggedInAt",
    "fullyChargedAt",
    "failedAt",
    "timeoutAt",
]
WALLET_DATE_KEYS = [
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


def last_charge_state(data: dict[str, Any]) -> str:
    """Process state for last charge (if available)."""
    return data["charges"][0]["state"] if len(data["charges"]) > 0 else None


def last_charge_extra_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Process extra attributes for last charge (if available)."""
    if data["charges"]:
        attributes = data["charges"][0]
        for key in CHARGE_POINT_DATE_KEYS:
            if key in attributes:
                attributes[key] = _parse_date(attributes[key])

        return attributes

    return None


def wallet_credit_extra_attribute(data: dict[str, Any]) -> dict[str, Any]:
    """Process extra attributes for last charge (if available)."""
    if data["balance"]:
        return {"credit": data["balance"]["credit"]}

    return None


def wallet_extra_attributes(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Process extra attributes for the wallet (if available)."""
    attributes = {}

    if data:
        for transaction in data:
            for key in WALLET_DATE_KEYS:
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


CHARGE_POINT_ENTITY_DESCRIPTIONS: tuple[MontaSensorEntityDescription, ...] = (
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
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
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
        key="monta-wallet-amount",
        name="Monta - Personal Wallet",
        icon="mdi:wallet",
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda data: data["balance"]["amount"]
        if data.get("balance")
        else None,
        extra_state_attributes_fn=wallet_credit_extra_attribute,
    ),
)

TRANSACTION_ENTITY_DESCRIPTIONS: tuple[MontaSensorEntityDescription, ...] = (
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="monta-latest-wallet-transactions",
        name="Monta - Latest Wallet Transactions",
        icon="mdi:wallet-outline",
        value_fn=lambda data: data,
        extra_state_attributes_fn=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for charge_point_id in coordinator.data[ATTR_CHARGE_POINTS]:
        async_add_entities(
            [
                MontaChargePointSensor(
                    coordinator,
                    entry,
                    description,
                    charge_point_id,
                )
                for description in CHARGE_POINT_ENTITY_DESCRIPTIONS
            ]
        )

    async_add_entities(
        [
            MontaWalletSensor(coordinator, entry, description)
            for description in WALLET_ENTITY_DESCRIPTIONS
        ]
    )
    async_add_entities(
        [
            MontaTransactionsSensor(coordinator, entry, description)
            for description in TRANSACTION_ENTITY_DESCRIPTIONS
        ]
    )


class MontaChargePointSensor(MontaEntity, SensorEntity):
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
            self.coordinator.data[ATTR_CHARGE_POINTS][self.charge_point_id]
        )

    @property
    def extra_attributes(self) -> str:
        """Return extra attributes for the sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        if self.entity_description.extra_state_attributes_fn:
            return self.entity_description.extra_state_attributes_fn(
                self.coordinator.data[ATTR_CHARGE_POINTS][self.charge_point_id]
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
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor."""
        if self.coordinator.data:
            wallet_data = self.coordinator.data.get(ATTR_WALLET, {})
            if wallet_currency := wallet_data.get("currency"):
                return wallet_currency.get("identifier", "").upper()

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.data[ATTR_WALLET])

    @property
    def extra_attributes(self) -> str:
        """Return extra attributes for the sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        if self.entity_description.extra_state_attributes_fn:
            return self.entity_description.extra_state_attributes_fn(
                self.coordinator.data[ATTR_WALLET]
            )
        return None


class MontaTransactionsSensor(
    CoordinatorEntity[MontaDataUpdateCoordinator], SensorEntity
):
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
            "monta_latest_transactions",
        )

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        transactions = self.coordinator.data.get(ATTR_TRANSACTIONS, [])
        if not transactions:
            return None
        return self.entity_description.value_fn(
            transactions[0]["state"]
        )

    @property
    def extra_attributes(self) -> str:
        """Return extra attributes for the sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Converts the dates to correct home assitant format."""
        attributes = {}

        if data := self.coordinator.data.get(ATTR_TRANSACTIONS, []):
            for transaction in data:
                for key in WALLET_DATE_KEYS:
                    if key in transaction:
                        transaction[key] = _parse_date(transaction[key])
            attributes["transactions"] = data

        return attributes
