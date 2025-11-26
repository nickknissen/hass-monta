"""Switch platform for monta."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id

from .const import DOMAIN, ChargerStatus
from .entity import MontaEntity
from .utils import snake_case

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MontaChargePointCoordinator

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="charger",
        name="Start/Stop",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    charge_point_coordinator = coordinators["charge_point"]

    for charge_point_id in charge_point_coordinator.data:
        async_add_devices(
            [
                MontaSwitch(
                    charge_point_coordinator,
                    description,
                    charge_point_id,
                )
                for description in ENTITY_DESCRIPTIONS
            ],
        )


class MontaSwitch(MontaEntity, SwitchEntity):
    """Monta switch class for controlling charge point charging."""

    _local_state: bool | None

    def __init__(
        self,
        coordinator: MontaChargePointCoordinator,
        entity_description: SwitchEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, charge_point_id)
        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{charge_point_id}_{snake_case(entity_description.key)}",
            [f"{charge_point_id}"],
        )
        self._local_state = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Reset local state when coordinator updates."""
        self._local_state = None
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return the availability of the switch."""
        return self.coordinator.data[self.charge_point_id].state not in {
            ChargerStatus.DISCONNECTED,
            ChargerStatus.ERROR,
        }

    @property
    def is_on(self) -> bool:
        """Return the status of pause/resume."""
        if self._local_state is not None:
            return self._local_state
        return self.coordinator.data[self.charge_point_id].state in {
            ChargerStatus.BUSY_CHARGING,
            ChargerStatus.BUSY,
            ChargerStatus.BUSY_SCHEDULED,
        }

    async def async_turn_on(self, **_: Any) -> None:  # noqa: ANN401
        """Start charger."""
        await self.coordinator.async_start_charge(self.charge_point_id)
        self._local_state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:  # noqa: ANN401
        """Stop charger."""
        await self.coordinator.async_stop_charge(self.charge_point_id)
        self._local_state = False
        self.async_write_ha_state()
