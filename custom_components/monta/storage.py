"""Token storage implementation for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from monta import TokenStorage

if TYPE_CHECKING:
    from homeassistant.helpers.storage import Store


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
