"""DataUpdateCoordinator for monta."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MontaApiClient, MontaApiClientAuthenticationError, MontaApiClientError
from .const import ATTR_CHARGEPOINTS, ATTR_WALLET, DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
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
            chargepoints = await self.client.async_get_charge_points()
            for charge_point_id in chargepoints.keys():
                chargepoints[charge_point_id][
                    "charges"
                ] = await self.client.async_get_charges(charge_point_id)
            wallet = await self.client.async_get_wallet_transactions()
            return {ATTR_CHARGEPOINTS: chargepoints, ATTR_WALLET: wallet}
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
