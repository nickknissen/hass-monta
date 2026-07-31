"""MontaEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MontaChargePointCoordinator
from .utils import snake_case

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def charge_point_unique_id(entry_id: str, charge_point_id: int, key: str) -> str:
    """Return the unique id of a charge point entity.

    Scoped to the config entry, because the same charger can be visible to
    two Monta accounts and each entry owns its own entities.
    """
    return f"{entry_id}_{charge_point_id}_{snake_case(key)}"


def account_unique_id(entry_id: str, key: str) -> str:
    """Return the unique id of an account wide entity, such as the wallet."""
    return f"{entry_id}_{snake_case(key)}"


def account_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the device representing the Monta account behind a config entry.

    The wallet and transaction sensors describe the account rather than any
    single charger, so they hang off this device instead of a charge point.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, f"account_{entry.entry_id}")},
        name=entry.title,
        manufacturer="Monta",
        entry_type=DeviceEntryType.SERVICE,
    )


class MontaEntity(CoordinatorEntity[MontaChargePointCoordinator]):
    """MontaEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    charge_point_id: int

    def __init__(
        self, coordinator: MontaChargePointCoordinator, charge_point_id: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.charge_point_id = charge_point_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Wallbox device."""
        chargepoint = self.coordinator.data[self.charge_point_id]
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    str(self.charge_point_id),
                ),
            },
            name=f"Monta - {chargepoint.name}",
            manufacturer=chargepoint.brand_name,
            model=chargepoint.model_name,
            sw_version=chargepoint.firmware_version,
        )
