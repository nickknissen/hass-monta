"""DataUpdateCoordinator for monta."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from monta import (
    MontaApiClient,
    MontaApiClientAuthenticationError,
    MontaApiClientError,
    MontaApiClientRateLimitError,
)
from monta.models import Charge, ChargePoint, Wallet, WalletTransaction

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

# Latest charges fetched per update cycle, across all charge points.
CHARGES_PER_UPDATE = 100


def _rate_limit_message(exception: MontaApiClientRateLimitError) -> str:
    """Build an UpdateFailed message for a rate-limited request."""
    if exception.retry_after is not None:
        return (
            "Monta API rate limit hit, API asks to retry after "
            f"{exception.retry_after}s; retrying on the next scheduled update"
        )
    return "Monta API rate limit hit; retrying on the next scheduled update"


class MontaChargePointCoordinator(DataUpdateCoordinator[dict[int, ChargePoint]]):
    """Coordinator for charge point data."""

    config_entry: ConfigEntry
    data: dict[int, ChargePoint]

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
            name=f"{DOMAIN}_charge_points",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[int, ChargePoint]:
        """Update charge point data via library.

        Uses two requests per cycle regardless of charger count: one
        paginated charge-point fetch and one bulk charges fetch, so accounts
        with many chargers stay under Monta's ~10 requests/minute limit.
        """
        try:
            charge_points = await self.client.async_get_all_charge_points()
            charges = await self.client.async_get_charges(
                per_page=CHARGES_PER_UPDATE,
            )
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientRateLimitError as exception:
            raise UpdateFailed(_rate_limit_message(exception)) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception

        charges_by_charge_point: dict[int, list[Charge]] = {}
        for charge in charges:
            charges_by_charge_point.setdefault(
                charge.charge_point_id, [],
            ).append(charge)

        for charge_point_id, charge_point in charge_points.items():
            if charge_point_id in charges_by_charge_point:
                charge_point.charges = charges_by_charge_point[charge_point_id]
            elif self.data and charge_point_id in self.data:
                # A charger with no charge in the latest batch keeps the
                # charges from the previous cycle instead of going empty.
                charge_point.charges = self.data[charge_point_id].charges

        return charge_points

    async def async_start_charge(self, charge_point_id: int) -> Charge:
        """Start a charge."""
        try:
            return await self.client.async_start_charge(charge_point_id)
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientRateLimitError as exception:
            raise UpdateFailed(_rate_limit_message(exception)) from exception
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
        except MontaApiClientRateLimitError as exception:
            raise UpdateFailed(_rate_limit_message(exception)) from exception
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
        except MontaApiClientRateLimitError as exception:
            raise UpdateFailed(_rate_limit_message(exception)) from exception
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
        except MontaApiClientRateLimitError as exception:
            raise UpdateFailed(_rate_limit_message(exception)) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception
