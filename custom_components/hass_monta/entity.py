"""MontaEntity class."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MontaChargePointCoordinator


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
