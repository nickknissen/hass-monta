"""Switch platform for monta."""
from __future__ import annotations

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id

from .const import DOMAIN, ChargerStatus
from .coordinator import MontaDataUpdateCoordinator
from .entity import MontaEntity
from .utils import snake_case

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="charger",
        name="Start/Stop",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    for charge_point_id, _ in coordinator.data.items():
        async_add_devices(
            [
                MontaSwitch(
                    coordinator,
                    description,
                    charge_point_id,
                )
                for description in ENTITY_DESCRIPTIONS
            ]
        )


class MontaSwitch(MontaEntity, SwitchEntity):
    """monta switch class."""

    def __init__(
        self,
        coordinator: MontaDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
        charge_point_id: int,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, charge_point_id)
        self.entity_description = entity_description
        self._attr_unique_id = generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{charge_point_id}_{snake_case(entity_description.key)}",
            [charge_point_id],
        )

    @property
    def available(self) -> bool:
        """Return the availability of the switch."""
        return self.coordinator.data[self.charge_point_id]["state"] not in {
            ChargerStatus.DISCONNECTED,
            ChargerStatus.ERROR,
        }

    @property
    def is_on(self) -> bool:
        """Return the status of pause/resume."""
        return self.coordinator.data[self.charge_point_id]["state"] in {
            ChargerStatus.BUSY_CHARGING,
            ChargerStatus.BUSY,
            ChargerStatus.BUSY_SCHEDULED,
        }

    async def async_turn_on(self, **_: any) -> None:
        """Start charger."""
        await self.coordinator.async_start_charge(self.charge_point_id)

    async def async_turn_off(self, **_: any) -> None:
        """Stop charger."""
        await self.coordinator.async_stop_charge(self.charge_point_id)
