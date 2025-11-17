"""API module for monta."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.helpers.storage import Store
from monta import (
    MontaApiClient as MontaApiClientBase,
    TokenStorage,
    MontaApiClientError,
    MontaApiClientAuthenticationError,
    MontaApiClientCommunicationError,
)

# Re-export exceptions for backward compatibility
__all__ = [
    "MontaApiClient",
    "MontaApiClientError",
    "MontaApiClientAuthenticationError",
    "MontaApiClientCommunicationError",
]


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


class MontaApiClient(MontaApiClientBase):
    """Monta API client wrapper for Home Assistant.

    This class extends the monta package's MontaApiClient to integrate
    with Home Assistant's storage system.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: aiohttp.ClientSession,
        store: Store,
    ) -> None:
        """Initialize the MontaApiClient with Home Assistant storage."""
        # Create a token storage adapter that uses Home Assistant's Store
        token_storage = HomeAssistantTokenStorage(store)

        # Initialize the base monta client with our custom storage
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            session=session,
            token_storage=token_storage,
        )
