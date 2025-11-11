"""API module for monta - Home Assistant integration wrapper."""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.helpers.storage import Store
from monta import (
    MontaApiClient as BaseMontaApiClient,
    TokenStorage,
)
from monta import (  # noqa: F401
    Charge,
    ChargePoint,
    MontaApiClientAuthenticationError,
    MontaApiClientCommunicationError,
    MontaApiClientError,
    Wallet,
    WalletTransaction,
)


class HomeAssistantTokenStorage(TokenStorage):
    """Home Assistant specific token storage implementation.

    This adapter wraps Home Assistant's Store to provide
    token persistence for the Monta API client.
    """

    def __init__(self, store: Store) -> None:
        """Initialize the Home Assistant token storage.

        Args:
            store: Home Assistant Store instance for persisting tokens
        """
        self._store = store
        self._data: dict[str, Any] | None = None

    async def load(self) -> dict[str, Any] | None:
        """Load stored token data from Home Assistant storage.

        Returns:
            Dictionary containing token data or None if not found
        """
        if self._data is None:
            self._data = await self._store.async_load()

        return self._data

    async def save(self, data: dict[str, Any]) -> None:
        """Save token data to Home Assistant storage.

        Args:
            data: Dictionary containing token data to persist
        """
        self._data = data
        await self._store.async_save(data)


class MontaApiClient:
    """Home Assistant wrapper for the Monta API client.

    This class maintains backward compatibility with the existing
    Home Assistant integration while using the standalone monta package.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: aiohttp.ClientSession,
        store: Store,
    ) -> None:
        """Initialize the MontaApiClient.

        Args:
            client_id: Monta API client ID
            client_secret: Monta API client secret
            session: aiohttp ClientSession for making requests
            store: Home Assistant Store for token persistence
        """
        # Create the token storage adapter
        token_storage = HomeAssistantTokenStorage(store)

        # Initialize the base client from the monta package
        self._client = BaseMontaApiClient(
            client_id=client_id,
            client_secret=client_secret,
            session=session,
            token_storage=token_storage,
        )

    async def async_request_token(self):
        """Obtain access token with clientId and secret."""
        return await self._client.async_request_token()

    async def async_authenticate(self) -> str:
        """Obtain access token and store it."""
        return await self._client.async_authenticate()

    async def async_get_charge_points(self) -> dict[int, ChargePoint]:
        """Get available charge points for the user."""
        return await self._client.async_get_charge_points()

    async def async_get_charges(self, charge_point_id: int) -> list[Charge]:
        """Retrieve a list of charges for a specific charge point."""
        return await self._client.async_get_charges(charge_point_id)

    async def async_start_charge(self, charge_point_id: int) -> Any:
        """Start a charge on the specified charge point."""
        return await self._client.async_start_charge(charge_point_id)

    async def async_stop_charge(self, charge_id: int) -> Any:
        """Stop a charge."""
        return await self._client.async_stop_charge(charge_id)

    async def async_get_wallet_transactions(self) -> list[WalletTransaction]:
        """Retrieve first page of wallet transactions."""
        return await self._client.async_get_wallet_transactions()

    async def async_get_personal_wallet(self) -> Wallet:
        """Retrieve personal wallet information."""
        return await self._client.async_get_personal_wallet()

    async def async_get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        return await self._client.async_get_access_token()


__all__ = [
    "MontaApiClient",
    "MontaApiClientError",
    "MontaApiClientCommunicationError",
    "MontaApiClientAuthenticationError",
    "ChargePoint",
    "Charge",
    "Wallet",
    "WalletTransaction",
]
