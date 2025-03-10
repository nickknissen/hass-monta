"""DataUpdateCoordinator for monta."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MontaApiClient, MontaApiClientAuthenticationError, MontaApiClientError
from .const import ATTR_CHARGE_POINTS, ATTR_TRANSACTIONS, ATTR_WALLET, DOMAIN, LOGGER


class MontaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, client: MontaApiClient) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            charge_points = await self.client.async_get_charge_points()
            for charge_point_id in charge_points:
                charge_points[charge_point_id][
                    "charges"
                ] = await self.client.async_get_charges(charge_point_id)

            personal_wallet = await self.client.async_get_personal_wallet()
            wallet_transactions = await self.client.async_get_wallet_transactions()

            return {
                ATTR_CHARGE_POINTS: charge_points,
                ATTR_WALLET: personal_wallet,
                ATTR_TRANSACTIONS: wallet_transactions,
            }
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception

    async def async_start_charge(self, charge_point_id: int):
        """Start a charge."""
        try:
            return await self.client.async_start_charge(charge_point_id)
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception

    async def async_stop_charge(self, charge_point_id: int):
        """Stop a charge."""

        charges = await self.client.async_get_charges(charge_point_id)

        try:
            return await self.client.async_stop_charge(charges[0]["id"])
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception
