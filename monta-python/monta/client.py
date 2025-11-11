"""API client for Monta."""

from __future__ import annotations

import asyncio
import logging
import socket
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import async_timeout

from .const import (
    API_BASE_URL,
    DEFAULT_TIMEOUT,
    PREEMPTIVE_REFRESH_TTL_IN_SECONDS,
    PRIVATE_INFORMATION,
)
from .exceptions import (
    MontaApiClientAuthenticationError,
    MontaApiClientCommunicationError,
    MontaApiClientError,
)
from .models import Charge, ChargePoint, TokenResponse, Wallet, WalletTransaction

_LOGGER = logging.getLogger(__name__)


class TokenStorage(ABC):
    """Abstract base class for token storage."""

    @abstractmethod
    async def load(self) -> dict[str, Any] | None:
        """Load stored token data."""

    @abstractmethod
    async def save(self, data: dict[str, Any]) -> None:
        """Save token data."""


class InMemoryTokenStorage(TokenStorage):
    """Simple in-memory token storage implementation."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._data: dict[str, Any] | None = None

    async def load(self) -> dict[str, Any] | None:
        """Load stored token data."""
        return self._data

    async def save(self, data: dict[str, Any]) -> None:
        """Save token data."""
        self._data = data


class MontaApiClient:
    """Represents a Monta API client.

    This class provides methods to interact with the Monta public API,
    such as obtaining an access token, retrieving available charges, and
    managing charging sessions.

    Usage example:
    ```python
    import aiohttp
    from monta import MontaApiClient

    async with aiohttp.ClientSession() as session:
        client = MontaApiClient(
            client_id="your_client_id",
            client_secret="your_client_secret",
            session=session,
        )
        chargers = await client.async_get_charge_points()
    ```
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: aiohttp.ClientSession,
        token_storage: TokenStorage | None = None,
    ) -> None:
        """Initialize the MontaApiClient.

        Args:
            client_id: Your Monta API client ID
            client_secret: Your Monta API client secret
            session: An aiohttp ClientSession for making requests
            token_storage: Optional custom token storage implementation.
                          If not provided, uses InMemoryTokenStorage.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._session = session
        self._token_storage = token_storage or InMemoryTokenStorage()
        self._token_data: dict[str, Any] | None = None
        self._get_token_lock = asyncio.Lock()

    async def async_request_token(self) -> TokenResponse:
        """Obtain access token with clientId and secret."""
        response_json = await self._api_wrapper(
            path="auth/token",
            method="post",
            data={"clientId": self._client_id, "clientSecret": self._client_secret},
        )

        return TokenResponse.from_dict(response_json)

    async def async_authenticate(self) -> str:
        """Obtain access token and store it."""
        token_response = await self.async_request_token()

        await self._async_update_token_data(
            token_response.access_token,
            token_response.access_token_expiration_date,
            token_response.refresh_token,
            token_response.refresh_token_expiration_date,
        )

        return token_response.access_token

    async def async_get_charge_points(self) -> dict[int, ChargePoint]:
        """Get available charge points for the user.

        Returns:
            A dictionary mapping charge point IDs to ChargePoint objects.
        """
        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="get",
            path="charge-points?page=0&perPage=10",
            headers={"authorization": f"Bearer {access_token}"},
        )

        return {
            item["id"]: ChargePoint.from_dict(item)
            for item in response["data"]
            if item.get("serialNumber") is not None
        }

    async def async_get_charges(self, charge_point_id: int) -> list[Charge]:
        """Retrieve a list of charges for a specific charge point.

        Args:
            charge_point_id: The ID of the charge point

        Returns:
            A list of Charge objects, sorted by ID (most recent first).
        """
        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="get",
            path=f"charges?chargePointId={charge_point_id}",
            headers={"authorization": f"Bearer {access_token}"},
        )

        charges = response.get("data")

        if charges is None:
            _LOGGER.warning("No charges found in response!")
            charges = []

        charge_objects = [Charge.from_dict(charge) for charge in charges]
        return sorted(charge_objects, key=lambda charge: -charge.id)

    async def async_start_charge(self, charge_point_id: int) -> Any:
        """Start a charge on the specified charge point.

        Args:
            charge_point_id: The ID of the charge point to start charging on

        Returns:
            The API response data.
        """
        access_token = await self.async_get_access_token()

        _LOGGER.debug("Trying to start a charge on: %s", charge_point_id)

        response = await self._api_wrapper(
            method="post",
            path="charges",
            headers={"authorization": f"Bearer {access_token}"},
            data={"chargePointId": charge_point_id},
        )

        _LOGGER.debug("Started a charge on: %s", charge_point_id)

        return response

    async def async_stop_charge(self, charge_id: int) -> Any:
        """Stop a charge.

        Args:
            charge_id: The ID of the charge to stop

        Returns:
            The API response data.
        """
        access_token = await self.async_get_access_token()

        _LOGGER.debug("Trying to stop a charge with id: %s", charge_id)

        response = await self._api_wrapper(
            method="post",
            path=f"charges/{charge_id}/stop",
            headers={"authorization": f"Bearer {access_token}"},
        )

        _LOGGER.debug("Stopped charge for chargeId: %s <%s>", charge_id, response)

        return response

    async def async_get_wallet_transactions(self) -> list[WalletTransaction]:
        """Retrieve first page of wallet transactions.

        Returns:
            A list of WalletTransaction objects, sorted by ID (most recent first).
        """
        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="get",
            path="wallet-transactions",
            headers={"authorization": f"Bearer {access_token}"},
        )

        transactions = response.get("data")

        if transactions is None:
            _LOGGER.warning("No transactions found in response!")
            transactions = []

        transaction_objects = [WalletTransaction.from_dict(tx) for tx in transactions]
        return sorted(transaction_objects, key=lambda transaction: -transaction.id)

    async def async_get_personal_wallet(self) -> Wallet:
        """Retrieve personal wallet information.

        Returns:
            A Wallet object containing balance and currency information.
        """
        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="get",
            path="wallets/personal",
            headers={"authorization": f"Bearer {access_token}"},
        )

        return Wallet.from_dict(response)

    async def async_get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            A valid access token.

        Raises:
            MontaApiClientAuthenticationError: If authentication fails.
        """
        async with self._get_token_lock:
            if self._token_data is None:
                await self._async_load_token_data()

            if self._is_access_token_valid():
                _LOGGER.debug("Access Token still valid, using it")
                return self._token_data["access_token"]

            if self._is_refresh_token_valid():
                _LOGGER.debug("Refresh Token still valid, using it")
                params = {"refreshToken": self._token_data["refresh_token"]}

                response_json = await self._api_wrapper(
                    path="auth/refresh",
                    method="post",
                    data=params,
                )

                token_response = TokenResponse.from_dict(response_json)

                await self._async_update_token_data(
                    token_response.access_token,
                    token_response.access_token_expiration_date,
                    token_response.refresh_token,
                    token_response.refresh_token_expiration_date,
                )

                return token_response.access_token

            _LOGGER.debug("No token is valid, requesting new tokens")
            return await self.async_authenticate()

    def _filter_private_information(self, data: Any) -> Any:
        """Filter private information from data for logging."""
        if isinstance(data, dict):
            filtered_data = {}
            for key, value in data.items():
                if isinstance(value, dict | list):
                    filtered_data[key] = self._filter_private_information(value)
                else:
                    filtered_data[key] = (
                        "*" * len(str(value)) if key in PRIVATE_INFORMATION else value
                    )
            return filtered_data
        elif isinstance(data, list):
            return [self._filter_private_information(item) for item in data]
        else:
            return data

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Make an API request.

        Args:
            method: HTTP method (get, post, etc.)
            path: API endpoint path
            data: Optional request body data
            headers: Optional request headers

        Returns:
            The JSON response from the API.

        Raises:
            MontaApiClientAuthenticationError: For 401/403 errors
            MontaApiClientCommunicationError: For network/timeout errors
            MontaApiClientError: For other errors
        """
        default_headers = {
            "Content-type": "application/json; charset=UTF-8",
            "accept": "application/json",
        }

        all_headers = {**default_headers, **(headers or {})}

        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT):
                response = await self._session.request(
                    method=method,
                    url=f"{API_BASE_URL}{path}",
                    headers=all_headers,
                    json=data,
                )

                _LOGGER.debug("[%s] Response header: %s", path, response.headers)
                _LOGGER.debug("[%s] Response status: %s", path, response.status)

                if response.status in (401, 403):
                    raise MontaApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                response_json = await response.json()

                _LOGGER.debug(
                    "[%s] Response body: %s",
                    path,
                    self._filter_private_information(response_json),
                )

                return response_json

        except asyncio.TimeoutError as exception:
            raise MontaApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise MontaApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except MontaApiClientAuthenticationError:
            raise
        except Exception as exception:
            raise MontaApiClientError("Something really wrong happened!") from exception

    async def _async_update_token_data(
        self,
        access_token: str | None,
        access_token_expiration: datetime | None,
        refresh_token: str | None,
        refresh_token_expiration: datetime | None,
    ) -> None:
        """Update token data in storage."""
        if self._token_data is None:
            await self._async_load_token_data()

        if access_token is not None:
            self._token_data["access_token"] = access_token
        if access_token_expiration is not None:
            self._token_data["access_token_expiration"] = access_token_expiration.isoformat()
        if refresh_token is not None:
            self._token_data["refresh_token"] = refresh_token
        if refresh_token_expiration is not None:
            self._token_data["refresh_token_expiration"] = refresh_token_expiration.isoformat()

        await self._token_storage.save(self._token_data)

    async def _async_load_token_data(self) -> None:
        """Load token data from storage."""
        self._token_data = await self._token_storage.load()

        if self._token_data is None:
            self._token_data = {
                "access_token": None,
                "refresh_token": None,
                "access_token_expiration": None,
                "refresh_token_expiration": None,
            }

    def _is_access_token_valid(self) -> bool:
        """Check if the access token is still valid."""
        if not self._token_data or not self._token_data.get("access_token"):
            return False

        expiration = self._token_data.get("access_token_expiration")
        if expiration is None:
            return False

        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration)

        preemptive_expire_time = expiration - timedelta(
            seconds=PREEMPTIVE_REFRESH_TTL_IN_SECONDS
        )

        return datetime.now(timezone.utc) < preemptive_expire_time

    def _is_refresh_token_valid(self) -> bool:
        """Check if the refresh token is still valid."""
        if not self._token_data or not self._token_data.get("refresh_token"):
            return False

        expiration = self._token_data.get("refresh_token_expiration")
        if expiration is None:
            return False

        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration)

        preemptive_expire_time = expiration - timedelta(
            seconds=PREEMPTIVE_REFRESH_TTL_IN_SECONDS
        )

        return datetime.now(timezone.utc) < preemptive_expire_time
