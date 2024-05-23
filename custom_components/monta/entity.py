"""MontaEntity class."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CHARGE_POINTS, ATTRIBUTION, DOMAIN
from .coordinator import MontaDataUpdateCoordinator


class MontaEntity(CoordinatorEntity[MontaDataUpdateCoordinator]):
    """MontaEntity class."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MontaDataUpdateCoordinator, charge_point_id: int
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.charge_point_id = charge_point_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Wallbox device."""
        chargepoint = self.coordinator.data[ATTR_CHARGE_POINTS][self.charge_point_id]
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self.charge_point_id,
                )
            },
            name=f"Monta - {chargepoint['name']}",
            manufacturer=chargepoint["brandName"],
            model=chargepoint["modelName"],
            sw_version=chargepoint["firmwareVersion"],
        )
