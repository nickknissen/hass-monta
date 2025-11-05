"""DataUpdateCoordinator for monta."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .api import MontaApiClient, MontaApiClientAuthenticationError, MontaApiClientError
from .const import ATTR_CHARGE_POINTS, ATTR_TRANSACTIONS, ATTR_WALLET, DOMAIN, LOGGER


class MontaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: MontaApiClient,
        scan_interval: int,
        scan_interval_charge_points: int,
        scan_interval_wallet: int,
        scan_interval_transactions: int,
    ) -> None:
        """Initialize."""
        self.client = client

        # Store individual scan intervals for each data type
        self.scan_interval_charge_points = scan_interval_charge_points
        self.scan_interval_wallet = scan_interval_wallet
        self.scan_interval_transactions = scan_interval_transactions

        # Track last update time for each data type
        self._last_update_charge_points: datetime | None = None
        self._last_update_wallet: datetime | None = None
        self._last_update_transactions: datetime | None = None

        # Use the smallest interval as the coordinator's update interval
        # so it runs frequently enough to check all data types
        min_interval = min(
            scan_interval_charge_points,
            scan_interval_wallet,
            scan_interval_transactions,
        )

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=min_interval),
        )

    def _should_update(self, last_update: datetime | None, interval: int) -> bool:
        """Check if data should be updated based on interval."""
        if last_update is None:
            return True
        now = dt_util.utcnow()
        return (now - last_update).total_seconds() >= interval

    async def _async_update_data(self):
        """Update data via library."""
        try:
            now = dt_util.utcnow()
            result = {}

            # Only fetch data if the interval has passed since last update
            # Start with existing data if available
            if self.data:
                result = self.data.copy()

            # Update charge points if interval has passed
            if self._should_update(
                self._last_update_charge_points, self.scan_interval_charge_points
            ):
                charge_points = await self.client.async_get_charge_points()
                for charge_point_id in charge_points:
                    charge_points[charge_point_id][
                        "charges"
                    ] = await self.client.async_get_charges(charge_point_id)
                result[ATTR_CHARGE_POINTS] = charge_points
                self._last_update_charge_points = now

            # Update wallet if interval has passed
            if self._should_update(
                self._last_update_wallet, self.scan_interval_wallet
            ):
                result[ATTR_WALLET] = await self.client.async_get_personal_wallet()
                self._last_update_wallet = now

            # Update transactions if interval has passed
            if self._should_update(
                self._last_update_transactions, self.scan_interval_transactions
            ):
                result[ATTR_TRANSACTIONS] = await self.client.async_get_wallet_transactions()
                self._last_update_transactions = now

            return result
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
