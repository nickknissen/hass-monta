"""MontaEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MontaDataUpdateCoordinator


class MontaEntity(CoordinatorEntity[MontaDataUpdateCoordinator]):
    """MontaEntity class."""

    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: MontaDataUpdateCoordinator, charge_point_id: int
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.charge_point_id = charge_point_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Wallbox device."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.charge_point_id,
                )
            },
            name=f"Monta - {self.coordinator.data[self.charge_point_id]['name']}",
            manufacturer=self.coordinator.data[self.charge_point_id]["brandName"],
            model=self.coordinator.data[self.charge_point_id]["modelName"],
            sw_version=self.coordinator.data[self.charge_point_id]["firmwareVersion"],
        )
