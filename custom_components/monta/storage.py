"""Token storage implementation for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store
from monta import TokenStorage

from .const import STORAGE_KEY, STORAGE_VERSION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def async_get_token_store(hass: HomeAssistant, entry_id: str) -> Store:
    """Return the token store belonging to a single config entry.

    Each config entry authenticates as its own Monta account, so the tokens
    must not be shared: a shared store lets one entry pick up (and refresh
    away) another entry's tokens.
    """
    return Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")


async def async_remove_legacy_token_store(hass: HomeAssistant) -> None:
    """Remove the pre-per-entry token store left behind by older versions."""
    await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()


class HomeAssistantTokenStorage(TokenStorage):
    """Token storage implementation using Home Assistant's Store."""

    def __init__(self, store: Store) -> None:
        """Initialize the Home Assistant token storage."""
        self._store = store

    async def load(self) -> dict[str, Any] | None:
        """Load token data from Home Assistant storage."""
        return await self._store.async_load()

    async def save(self, data: dict[str, Any]) -> None:
        """Save token data to Home Assistant storage."""
        await self._store.async_save(data)
