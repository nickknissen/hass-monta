"""DataUpdateCoordinator for monta."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

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
    from collections.abc import Callable, Coroutine

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

# Latest charges fetched per update cycle, across all charge points.
CHARGES_PER_UPDATE = 100

# States in which a charge record no longer changes server-side. Any state
# change after these comes from a new charge, which by having a newer id is
# guaranteed to appear in the bulk batch.
CHARGE_TERMINAL_STATES = {ChargeState.STOPPED.value, ChargeState.COMPLETED.value}

_DataT = TypeVar("_DataT")
_T = TypeVar("_T")


def _rate_limit_message(exception: MontaApiClientRateLimitError) -> str:
    """Build an UpdateFailed message for a rate-limited request."""
    if exception.retry_after is not None:
        return (
            "Monta API rate limit hit, API asks to retry after "
            f"{exception.retry_after}s; retrying on the next scheduled update"
        )
    return "Monta API rate limit hit; retrying on the next scheduled update"


class MontaAuthGuard:
    """Replaces rejected tokens using the credentials already configured.

    Monta access tokens live for an hour and refresh tokens rotate, so a 401
    almost always means the cached tokens went stale rather than that the
    client id and secret stopped working: those are long lived and the user
    never has to touch them. Minting a new token set from the stored
    credentials therefore settles nearly every authentication failure without
    involving the user at all.

    One guard is shared by the coordinators of a config entry, because they
    share the client and its tokens. Without that, a single expiry would have
    all three of them minting tokens at once and invalidating each other's.
    """

    def __init__(self, client: MontaApiClient) -> None:
        """Initialize."""
        self._client = client
        self._lock = asyncio.Lock()
        self._generation = 0

    @property
    def generation(self) -> int:
        """Return a counter identifying the current set of tokens."""
        return self._generation

    async def async_reauthenticate(self, generation: int) -> None:
        """Mint a new token set, unless another caller just did so.

        Pass the generation read before the failing request: if it no longer
        matches, the tokens that request failed with have already been
        replaced and retrying is enough.
        """
        async with self._lock:
            if generation != self._generation:
                return
            await self._client.async_authenticate()
            self._generation += 1


class MontaCoordinator(DataUpdateCoordinator[_DataT]):
    """Shared API error handling for the Monta coordinators."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MontaApiClient,
        auth: MontaAuthGuard,
        name: str,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        self.client = client
        self._auth = auth
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=name,
            config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_call_api(
        self,
        action: Callable[[], Coroutine[Any, Any, _T]],
    ) -> _T:
        """Run an API call, translating the library's errors for the caller.

        A rejected token is re-minted from the configured credentials and the
        call retried once, so only credentials the API itself refuses reach
        ConfigEntryAuthFailed and ask the user to reauthenticate.

        The action can be run twice, so it has to be safe to repeat.
        """
        generation = self._auth.generation
        try:
            try:
                return await action()
            except MontaApiClientAuthenticationError:
                LOGGER.debug(
                    "%s: Monta rejected the access token, re-authenticating "
                    "with the configured credentials",
                    self.name,
                )
                await self._auth.async_reauthenticate(generation)
                return await action()
        except MontaApiClientAuthenticationError as exception:
            # Raised by the re-authentication or by the retry after it: the
            # client id and secret themselves are no longer accepted, which
            # only the user can put right.
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientRateLimitError as exception:
            raise UpdateFailed(_rate_limit_message(exception)) from exception
        except MontaApiClientError as exception:
            raise UpdateFailed(exception) from exception


class MontaChargePointCoordinator(MontaCoordinator[dict[int, ChargePoint]]):
    """Coordinator for charge point data."""

    data: dict[int, ChargePoint]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MontaApiClient,
        auth: MontaAuthGuard,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        self._backfilled_charge_points: set[int] = set()
        super().__init__(
            hass=hass,
            entry=entry,
            client=client,
            auth=auth,
            name=f"{DOMAIN}_charge_points",
            scan_interval=scan_interval,
        )

    async def _async_update_data(self) -> dict[int, ChargePoint]:
        """Update charge point data via library."""
        return await self._async_call_api(self._async_fetch_charge_points)

    async def _async_fetch_charge_points(self) -> dict[int, ChargePoint]:
        """Fetch every charge point together with its charges.

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
        charge_points = await self.client.async_get_all_charge_points()
        charges = await self.client.async_get_charges(
            per_page=CHARGES_PER_UPDATE,
        )

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

        backfilled: set[int] = set()
        for charge_point_id in needs_fetch:
            try:
                fetched = await self.client.async_get_charges(charge_point_id)
            except MontaApiClientRateLimitError:
                # Keep the bulk data already gathered; chargers not yet
                # fetched stay pending and are retried next cycle.
                LOGGER.warning(
                    "Rate limited while fetching charges for charge point "
                    "%s; retrying on the next scheduled update",
                    charge_point_id,
                )
                break
            backfilled.add(charge_point_id)
            charge_points[charge_point_id].charges = fetched

        # Recorded only once the whole fetch has come through, because a
        # rejected token sends this method back to the top: a charger marked
        # on the abandoned attempt would be taken for done on the retry and
        # keep the empty charges it was left with, for good.
        self._backfilled_charge_points |= backfilled

        return charge_points

    def _previous_charges(self, charge_point_id: int) -> list[Charge]:
        """Return the charges fetched for a charge point in earlier cycles."""
        if self.data and charge_point_id in self.data:
            return self.data[charge_point_id].charges
        return []

    async def async_start_charge(self, charge_point_id: int) -> Charge:
        """Start a charge."""
        return await self._async_call_api(
            partial(self.client.async_start_charge, charge_point_id),
        )

    async def async_stop_charge(self, charge_point_id: int) -> Charge:
        """Stop a charge."""
        return await self._async_call_api(
            partial(self._async_stop_latest_charge, charge_point_id),
        )

    async def _async_stop_latest_charge(self, charge_point_id: int) -> Charge:
        """Stop whichever charge the charge point is running."""
        charges = await self.client.async_get_charges(charge_point_id)
        if not charges:
            msg = f"No active charges found for charge point {charge_point_id}"
            raise UpdateFailed(msg)
        return await self.client.async_stop_charge(charges[0].id)


class MontaWalletCoordinator(MontaCoordinator[Wallet]):
    """Coordinator for wallet data."""

    data: Wallet

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MontaApiClient,
        auth: MontaAuthGuard,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            entry=entry,
            client=client,
            auth=auth,
            name=f"{DOMAIN}_wallet",
            scan_interval=scan_interval,
        )

    async def _async_update_data(self) -> Wallet:
        """Update wallet data via library."""
        return await self._async_call_api(self.client.async_get_personal_wallet)


class MontaTransactionCoordinator(MontaCoordinator[list[WalletTransaction]]):
    """Coordinator for transaction data."""

    data: list[WalletTransaction]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MontaApiClient,
        auth: MontaAuthGuard,
        scan_interval: int,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            entry=entry,
            client=client,
            auth=auth,
            name=f"{DOMAIN}_transactions",
            scan_interval=scan_interval,
        )

    async def _async_update_data(self) -> list[WalletTransaction]:
        """Update transaction data via library."""
        return await self._async_call_api(self.client.async_get_wallet_transactions)
