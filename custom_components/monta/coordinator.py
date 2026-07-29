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
from monta.models import Charge, ChargePoint, ChargeState, Wallet, WalletTransaction

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

# Latest charges fetched per update cycle, across all charge points.
CHARGES_PER_UPDATE = 100

# States in which a charge record no longer changes server-side. Any state
# change after these comes from a new charge, which by having a newer id is
# guaranteed to appear in the bulk batch.
CHARGE_TERMINAL_STATES = {ChargeState.STOPPED.value, ChargeState.COMPLETED.value}


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
        self._backfilled_charge_points: set[int] = set()
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

        Chargers absent from the bulk batch get a targeted fetch when their
        data can't be derived from it: once ever for chargers never seen
        with a charge, and every cycle while their latest known charge is
        still active (its record mutates server-side). A retained terminal
        charge never goes stale, since any state change comes from a newer
        charge that is guaranteed to appear in the batch.
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

        needs_fetch: list[int] = []
        for charge_point_id, charge_point in charge_points.items():
            if charge_point_id in charges_by_charge_point:
                charge_point.charges = charges_by_charge_point[charge_point_id]
                continue
            previous_charges = self._previous_charges(charge_point_id)
            if previous_charges:
                # Keep the previous cycle's charges instead of going empty;
                # also serves as the fallback if the fetch below rate-limits.
                charge_point.charges = previous_charges
                if previous_charges[0].state not in CHARGE_TERMINAL_STATES:
                    # Still active: the record mutates, so refetch it.
                    needs_fetch.append(charge_point_id)
            elif charge_point_id not in self._backfilled_charge_points:
                needs_fetch.append(charge_point_id)

        for charge_point_id in needs_fetch:
            try:
                fetched = await self.client.async_get_charges(charge_point_id)
            except MontaApiClientAuthenticationError as exception:
                raise ConfigEntryAuthFailed(exception) from exception
            except MontaApiClientRateLimitError:
                # Keep the bulk data already gathered; chargers not yet
                # fetched stay pending and are retried next cycle.
                LOGGER.warning(
                    "Rate limited while fetching charges for charge point "
                    "%s; retrying on the next scheduled update",
                    charge_point_id,
                )
                break
            except MontaApiClientError as exception:
                raise UpdateFailed(exception) from exception
            self._backfilled_charge_points.add(charge_point_id)
            charge_points[charge_point_id].charges = fetched

        return charge_points

    def _previous_charges(self, charge_point_id: int) -> list[Charge]:
        """Return the charges fetched for a charge point in earlier cycles."""
        if self.data and charge_point_id in self.data:
            return self.data[charge_point_id].charges
        return []

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
