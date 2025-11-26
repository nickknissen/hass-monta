"""Sensor platform for monta."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfEnergy,
)
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    DOMAIN,
    ChargerStatus,
)
from .coordinator import (
    MontaChargePointCoordinator,
    MontaTransactionCoordinator,
    MontaWalletCoordinator,
)
from .entity import MontaEntity
from .utils import snake_case

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType
    from monta import ChargePoint, Wallet, WalletTransaction


@dataclass
class MontaSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[Any], StateType]
    extra_state_attributes_fn: Callable[[Any], dict[str, Any] | None] | None


@dataclass
class MontaSensorEntityDescription(
    SensorEntityDescription, MontaSensorEntityDescriptionMixin,
):
    """Describes MontaSensor sensor entity."""


def last_charge_state(data: ChargePoint) -> str | None:
    """Process state for last charge (if available)."""
    return data.charges[0].state if len(data.charges) > 0 else None


def last_charge_extra_attributes(data: ChargePoint) -> dict[str, Any] | None:
    """Process extra attributes for last charge (if available)."""
    if data.charges:
        # Convert the Charge object back to dict for Home Assistant attributes
        return data.charges[0].to_dict()

    return None


def wallet_credit_extra_attribute(data: Wallet) -> dict[str, Any] | None:
    """Process extra attributes for last charge (if available)."""
    if data.balance:
        return {"credit": data.balance.credit}

    return None


def wallet_extra_attributes(data: list[WalletTransaction]) -> dict[str, Any]:
    """Process extra attributes for the wallet (if available)."""
    attributes = {}

    if data:
        # Convert WalletTransaction objects to dicts for Home Assistant attributes
        attributes["transactions"] = [tx.to_dict() for tx in data]

    return attributes


CHARGE_POINT_ENTITY_DESCRIPTIONS: tuple[MontaSensorEntityDescription, ...] = (
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_visibility",
        translation_key="charger_visibility",
        icon="mdi:eye",
        device_class=SensorDeviceClass.ENUM,
        options=["public", "private"],
        value_fn=lambda data: data.visibility,
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_type",
        translation_key="charger_type",
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.ENUM,
        options=["ac", "dc"],
        value_fn=lambda data: data.type,
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_state",
        translation_key="charger_state",
        icon="mdi:state-machine",
        device_class=SensorDeviceClass.ENUM,
        options=[x.value for x in ChargerStatus],
        value_fn=lambda data: data.state,
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charger_lastMeterReadingKwh",
        translation_key="charger_lastmeterreadingkwh",
        icon="mdi:wallet",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.last_meter_reading_kwh,
        extra_state_attributes_fn=None,
    ),
    MontaSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="charge_state",
        translation_key="charge_state",
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
        value_fn=lambda data: data.balance.amount if data.balance else None,
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
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    charge_point_coordinator = coordinators["charge_point"]
    wallet_coordinator = coordinators["wallet"]
    transaction_coordinator = coordinators["transaction"]

    for charge_point_id in charge_point_coordinator.data:
        async_add_entities(
            [
                MontaChargePointSensor(
                    charge_point_coordinator,
                    entry,
                    description,
                    charge_point_id,
                )
                for description in CHARGE_POINT_ENTITY_DESCRIPTIONS
            ],
        )

    async_add_entities(
        [
            MontaWalletSensor(wallet_coordinator, entry, description)
            for description in WALLET_ENTITY_DESCRIPTIONS
        ],
    )
    async_add_entities(
        [
            MontaTransactionsSensor(transaction_coordinator, entry, description)
            for description in TRANSACTION_ENTITY_DESCRIPTIONS
        ],
    )


class MontaChargePointSensor(MontaEntity, SensorEntity):
    """monta Sensor class."""

    entity_description: MontaSensorEntityDescription

    def __init__(
        self,
        coordinator: MontaChargePointCoordinator,
        _: ConfigEntry,
        entity_description: MontaSensorEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, charge_point_id)

        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{charge_point_id}_{snake_case(entity_description.key)}",
            [str(charge_point_id)],
        )

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self.entity_description.value_fn(
            self.coordinator.data[self.charge_point_id],
        )

    @property
    def extra_attributes(self) -> None:
        """Return extra attributes for the sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.entity_description.extra_state_attributes_fn:
            return self.entity_description.extra_state_attributes_fn(
                self.coordinator.data[self.charge_point_id],
            )
        return None


class MontaWalletSensor(CoordinatorEntity[MontaWalletCoordinator], SensorEntity):
    """monta Sensor class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: MontaSensorEntityDescription

    def __init__(
        self,
        coordinator: MontaWalletCoordinator,
        _: ConfigEntry,
        entity_description: MontaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"monta_{snake_case(entity_description.key)}",
            ["personal_monta_wallet"],
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor."""
        if self.coordinator.data and self.coordinator.data.currency:
            return self.coordinator.data.currency.identifier.upper()
        return None

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_attributes(self) -> None:
        """Return extra attributes for the sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.entity_description.extra_state_attributes_fn:
            return self.entity_description.extra_state_attributes_fn(
                self.coordinator.data,
            )
        return None


class MontaTransactionsSensor(
    CoordinatorEntity[MontaTransactionCoordinator], SensorEntity,
):
    """monta Sensor class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: MontaSensorEntityDescription

    def __init__(
        self,
        coordinator: MontaTransactionCoordinator,
        _: ConfigEntry,
        entity_description: MontaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)

        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"monta_{snake_case(entity_description.key)}",
            ["monta_latest_transactions"],
        )

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        transactions = self.coordinator.data if self.coordinator.data else []
        if not transactions:
            return None
        return transactions[0].state

    @property
    def extra_attributes(self) -> None:
        """Return extra attributes for the sensor."""
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Converts the dates to correct home assistant format."""
        attributes: dict[str, Any] = {}

        if data := self.coordinator.data:
            # Convert WalletTransaction objects to dicts for Home Assistant attributes
            attributes["transactions"] = [tx.to_dict() for tx in data]

        return attributes
