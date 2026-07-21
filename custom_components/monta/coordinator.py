"""DataUpdateCoordinator for monta."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from monta import (
    MontaApiClient,
    MontaApiClientAuthenticationError,
    MontaApiClientError,
)
from monta.models import Charge, ChargePoint, Wallet, WalletTransaction

from .const import DEFAULT_CHARGE_POINT_REQUEST_DELAY, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


class MontaChargePointCoordinator(DataUpdateCoordinator[dict[int, ChargePoint]]):
    """Coordinator for charge point data."""

    config_entry: ConfigEntry
    data: dict[int, ChargePoint]

    def __init__(
        self,
        hass: HomeAssistant,
        client: MontaApiClient,
        scan_interval: int,
        request_delay: float = DEFAULT_CHARGE_POINT_REQUEST_DELAY,
    ) -> None:
        """Initialize."""
        self.client = client
        self.request_delay = request_delay
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_charge_points",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[int, ChargePoint]:
        """Update charge point data via library.

        The detail call for each charge point is spaced out by
        ``request_delay`` seconds so that accounts with many chargers stay
        within Monta's ~10 requests/minute limit and don't trigger HTTP 429.
        """
        try:
            charge_points = await self.client.async_get_charge_points()
            for index, charge_point_id in enumerate(charge_points):
                # Throttle between detail calls (not before the first one).
                if index > 0 and self.request_delay > 0:
                    await asyncio.sleep(self.request_delay)
                charge_points[
                    charge_point_id
                ].charges = await self.client.async_get_charges(charge_point_id)
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception
        else:
            return charge_points

    async def async_start_charge(self, charge_point_id: int) -> Charge:
        """Start a charge."""
        try:
            return await self.client.async_start_charge(charge_point_id)
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception

    async def async_stop_charge(self, charge_point_id: int) -> Charge:
        """Stop a charge."""
        try:
            charges = await self.client.async_get_charges(charge_point_id)
            if not charges:
                msg = f"No active charges found for charge point {charge_point_id}"
                raise UpdateFailed(
                    msg,
                )
            return await self.client.async_stop_charge(charges[0].id)
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception


class MontaWalletCoordinator(DataUpdateCoordinator[Wallet]):
    """Coordinator for wallet data."""

    config_entry: ConfigEntry
    data: Wallet

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

    async def _async_update_data(self) -> Wallet:
        """Update wallet data via library."""
        try:
            return await self.client.async_get_personal_wallet()
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception


class MontaTransactionCoordinator(DataUpdateCoordinator[list[WalletTransaction]]):
    """Coordinator for transaction data."""

    config_entry: ConfigEntry
    data: list[WalletTransaction]

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

    async def _async_update_data(self) -> list[WalletTransaction]:
        """Update transaction data via library."""
        try:
            return await self.client.async_get_wallet_transactions()
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception
