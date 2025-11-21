"""Custom integration to integrate monta with Home Assistant.

For more details about this integration, please refer to
https://github.com/nickknissen/hass-monta
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from monta import MontaApiClient

from .const import (
    CONF_SCAN_INTERVAL_CHARGE_POINTS,
    CONF_SCAN_INTERVAL_TRANSACTIONS,
    CONF_SCAN_INTERVAL_WALLET,
    DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
    DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
    DEFAULT_SCAN_INTERVAL_WALLET,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .coordinator import (
    MontaChargePointCoordinator,
    MontaTransactionCoordinator,
    MontaWalletCoordinator,
)
from .services import async_setup_services
from .storage import HomeAssistantTokenStorage

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_remove()

    # Get individual scan intervals for each data type
    scan_interval_charge_points = entry.options.get(
        CONF_SCAN_INTERVAL_CHARGE_POINTS,
        entry.data.get(
            CONF_SCAN_INTERVAL_CHARGE_POINTS, DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
        ),
    )
    scan_interval_wallet = entry.options.get(
        CONF_SCAN_INTERVAL_WALLET,
        entry.data.get(CONF_SCAN_INTERVAL_WALLET, DEFAULT_SCAN_INTERVAL_WALLET),
    )
    scan_interval_transactions = entry.options.get(
        CONF_SCAN_INTERVAL_TRANSACTIONS,
        entry.data.get(
            CONF_SCAN_INTERVAL_TRANSACTIONS, DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
        ),
    )

    # Create API client shared by all coordinators
    client = MontaApiClient(
        client_id=entry.data[CONF_CLIENT_ID],
        client_secret=entry.data[CONF_CLIENT_SECRET],
        session=async_get_clientsession(hass),
        token_storage=HomeAssistantTokenStorage(store),
    )

    # Create separate coordinators for each data type
    charge_point_coordinator = MontaChargePointCoordinator(
        hass=hass,
        client=client,
        scan_interval=scan_interval_charge_points,
    )
    wallet_coordinator = MontaWalletCoordinator(
        hass=hass,
        client=client,
        scan_interval=scan_interval_wallet,
    )
    transaction_coordinator = MontaTransactionCoordinator(
        hass=hass,
        client=client,
        scan_interval=scan_interval_transactions,
    )

    # Store coordinators in a dictionary
    hass.data[DOMAIN][entry.entry_id] = {
        "charge_point": charge_point_coordinator,
        "wallet": wallet_coordinator,
        "transaction": transaction_coordinator,
    }

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    # Refresh all coordinators
    await charge_point_coordinator.async_config_entry_first_refresh()
    await wallet_coordinator.async_config_entry_first_refresh()
    await transaction_coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass, entry)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
