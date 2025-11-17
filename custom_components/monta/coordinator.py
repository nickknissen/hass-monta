"""DataUpdateCoordinator for monta."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from monta import (
    MontaApiClient,
    MontaApiClientAuthenticationError,
    MontaApiClientError,
)

from .const import DOMAIN, LOGGER


class MontaChargePointCoordinator(DataUpdateCoordinator):
    """Coordinator for charge point data.

    This coordinator manages data updates for Monta charge points, including
    their status, meter readings, and recent charging sessions. It handles
    API communication and automatic re-authentication when needed.

    Attributes:
        config_entry: The config entry associated with this coordinator
        client: MontaApiClient instance for API communication
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: MontaApiClient,
        scan_interval: int,
    ) -> None:
        """Initialize the charge point coordinator.

        Args:
            hass: Home Assistant instance
            client: MontaApiClient for API communication
            scan_interval: Update interval in seconds
        """
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_charge_points",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Update charge point data via library.

        Fetches all charge points and their recent charges from the Monta API.
        Handles authentication errors by triggering a re-authentication flow,
        and other API errors by marking the update as failed.

        Returns:
            Dictionary of charge points keyed by charge point ID

        Raises:
            ConfigEntryAuthFailed: When authentication fails (triggers re-auth)
            UpdateFailed: When API communication fails
        """
        try:
            # Fetch all charge points for the authenticated user
            charge_points = await self.client.async_get_charge_points()
            # For each charge point, fetch recent charging sessions
            for charge_point_id in charge_points:
                charge_points[charge_point_id].charges = (
                    await self.client.async_get_charges(charge_point_id)
                )
            return charge_points
        except MontaApiClientAuthenticationError as exception:
            # Trigger re-authentication flow in Home Assistant
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            # Mark update as failed, will retry on next interval
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
            return await self.client.async_stop_charge(charges[0].id)
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception


class MontaWalletCoordinator(DataUpdateCoordinator):
    """Coordinator for wallet data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: MontaApiClient,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_wallet",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Update wallet data via library."""
        try:
            return await self.client.async_get_personal_wallet()
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception


class MontaTransactionCoordinator(DataUpdateCoordinator):
    """Coordinator for transaction data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: MontaApiClient,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_transactions",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        """Update transaction data via library."""
        try:
            return await self.client.async_get_wallet_transactions()
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception
