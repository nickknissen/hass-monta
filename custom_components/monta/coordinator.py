"""DataUpdateCoordinator for monta."""

from __future__ import annotations

from datetime import timedelta, datetime
import random

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    MontaApiClient,
    MontaApiClientAuthenticationError,
    MontaApiClientError,
    MontaApiClientRateLimitError,
)
from .const import (
    ATTR_CHARGE_POINTS,
    ATTR_TRANSACTIONS,
    ATTR_WALLET,
    DOMAIN,
    LOGGER,
    BASE_UPDATE_INTERVAL_SECONDS,
    MAX_UPDATE_INTERVAL_SECONDS,
    CHARGE_POINTS_REFRESH_INTERVAL_SECONDS,
    WALLET_REFRESH_INTERVAL_SECONDS,
    DEFAULT_CHARGES_BATCH_SIZE,
)


class MontaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, client: MontaApiClient) -> None:
        """Initialize."""
        self.client = client
        # Caches for staggered fetching
        self._charge_points_cache: dict | None = None
        self._charge_points_last_refresh: datetime | None = None
        self._wallet_cache: dict | None = None
        self._transactions_cache: list | None = None
        self._wallet_last_refresh: datetime | None = None
        self._charges_index: int = 0
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=BASE_UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            # Step 1: Ensure charge points cache is populated and refreshed infrequently
            refresh_charge_points = False
            now = dt_util.utcnow()
            if self._charge_points_cache is None:
                refresh_charge_points = True
            elif self._charge_points_last_refresh is None:
                refresh_charge_points = True
            else:
                elapsed = (now - self._charge_points_last_refresh).total_seconds()
                refresh_charge_points = elapsed >= CHARGE_POINTS_REFRESH_INTERVAL_SECONDS

            if refresh_charge_points:
                charge_points = await self.client.async_get_charge_points()
                # Ensure each charge point has a charges list placeholder
                for _cp_id, cp in charge_points.items():
                    cp.setdefault("charges", [])
                self._charge_points_cache = charge_points
                self._charge_points_last_refresh = now
                # Reset charges index if the set changes
                self._charges_index = 0

            # Step 2: Stagger fetching of charges across cycles
            cp_ids = list(self._charge_points_cache.keys()) if self._charge_points_cache else []
            num_cps = len(cp_ids)

            # Batch size: never exceed the safe default or total count
            batch_size = min(DEFAULT_CHARGES_BATCH_SIZE, num_cps)

            if batch_size > 0:
                # Fetch charges for round-robin selected charge points
                for i in range(batch_size):
                    idx = (self._charges_index + i) % num_cps
                    cp_id = cp_ids[idx]
                    charges = await self.client.async_get_charges(cp_id)
                    # Update the cache
                    if self._charge_points_cache is not None and cp_id in self._charge_points_cache:
                        self._charge_points_cache[cp_id]["charges"] = charges

                # Advance index for next cycle
                self._charges_index = (self._charges_index + batch_size) % num_cps

            # Step 3: Wallet and transactions at a slower cadence (time-based)
            should_refresh_wallet = (
                self._wallet_last_refresh is None
                or (now - self._wallet_last_refresh).total_seconds() >= WALLET_REFRESH_INTERVAL_SECONDS
            )

            if should_refresh_wallet:
                self._wallet_cache = await self.client.async_get_personal_wallet()
                self._transactions_cache = await self.client.async_get_wallet_transactions()
                self._wallet_last_refresh = now

            result = {
                ATTR_CHARGE_POINTS: self._charge_points_cache or {},
                ATTR_WALLET: self._wallet_cache or {},
                ATTR_TRANSACTIONS: self._transactions_cache or [],
            }
            # If we had increased the interval previously due to 429, reset to base after a successful cycle
            base = BASE_UPDATE_INTERVAL_SECONDS
            if int(self.update_interval.total_seconds()) > base:
                self.update_interval = timedelta(seconds=base)
                self.logger.debug("Reset update interval to base %ss after successful cycle", base)
            return result
        except MontaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MontaApiClientRateLimitError as exception:
            # Increase update interval dynamically based on retry_after
            retry_after = exception.retry_after_seconds or 5
            jitter = random.uniform(0, 3)
            new_interval = min(
                MAX_UPDATE_INTERVAL_SECONDS,
                max(
                    int(self.update_interval.total_seconds()),
                    int(retry_after) + 2 + int(jitter),
                ),
            )
            self.update_interval = timedelta(seconds=new_interval)
            self.logger.info(
                "Rate limited by API. Backing off update interval to %ss (retry_after=%ss)",
                new_interval,
                retry_after,
            )
            raise UpdateFailed(exception) from exception
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
