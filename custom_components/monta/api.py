"""API module for monta."""
from __future__ import annotations

import asyncio
import socket
import logging
import json
from datetime import timedelta

import aiohttp
import async_timeout

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    STORAGE_ACCESS_TOKEN,
    STORAGE_ACCESS_EXPIRE_TIME,
    STORAGE_REFRESH_TOKEN,
    STORAGE_REFRESH_EXPIRE_TIME,
    PREEMPTIVE_REFRESH_TTL_IN_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class MontaApiClientError(Exception):
    """Exception to indicate a general API error."""


class MontaApiClientCommunicationError(MontaApiClientError):
    """Exception to indicate a communication error."""


class MontaApiClientAuthenticationError(MontaApiClientError):
    """Exception to indicate an authentication error."""


class MontaApiClient:
    """Represents a Monta API client.

    This class provides methods to interact with the Monta public API,
    such as obtaining an access token, retrieving available charges, and
    updating user preferences.

    Usage example:
    ```
    client = MontaApiClient(client_id, client_secret, session, store)
    access_token = await client.async_request_access_token()
    chargers = await client.async_get_charge_points().
    ```
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: aiohttp.ClientSession,
        store: Store,
    ) -> None:
        """Initialize the MontaApiClient."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._session = session

        self._prefs = None
        self._store = store

        self._get_token_lock = asyncio.Lock()

    async def async_request_token(self) -> any:
        """Obtain access token with clientId and secret."""

        params = {"clientId": self._client_id, "clientSecret": self._client_secret}
        _LOGGER.debug(
            "Requesting access token with: %s",
            json.dumps(params),
        )

        response_json = await self._api_wrapper(
            path="auth/token",
            method="post",
            data=params,
        )

        return response_json

    async def async_authenticate(self) -> str:
        """Obtain access token and store it in preferences."""

        response_json = await self.async_request_token()

        await self._async_update_preferences(
            response_json["accessToken"],
            dt_util.parse_datetime(response_json["accessTokenExpirationDate"]),
            response_json["refreshToken"],
            dt_util.parse_datetime(response_json["refreshTokenExpirationDate"]),
        )

        return response_json["accessToken"]

    async def async_get_charge_points(self) -> any:
        """Get availbe charge points to the user."""

        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="get",
            path="charge-points?page=0&perPage=10",
            headers={"authorization": f"Bearer {access_token}"},
        )

        _LOGGER.debug("Fetched charge points %s", json.dumps(response))

        return {item["id"]: item for item in response["data"]}

    async def async_get_charges(self, charge_point_id: int) -> any:
        """Retrieve a list of charge."""

        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="get",
            path=f"charges?chargePointId={charge_point_id}",
            headers={"authorization": f"Bearer {access_token}"},
        )

        _LOGGER.debug("Fetched charges %s", json.dumps(response))

        return sorted(response["data"], key=lambda charge: -charge["id"])

    async def async_start_charge(self, charge_point_id: int) -> any:
        """Start a charge."""
        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="post",
            path="charges",
            headers={"authorization": f"Bearer {access_token}"},
            data={"chargePointId": charge_point_id},
        )

        _LOGGER.debug("Started a charge: %s", json.dumps(response))

        return response

    async def async_stop_charge(self, charge_id: int) -> any:
        """Start a charge."""
        access_token = await self.async_get_access_token()

        response = await self._api_wrapper(
            method="post",
            path=f"charges/{charge_id}/stop",
            headers={"authorization": f"Bearer {access_token}"},
        )

        _LOGGER.debug("Stopped charge: %s", json.dumps(response))

        return response

    async def async_get_access_token(self) -> str:
        """Get access token."""
        async with self._get_token_lock:
            if self._prefs is None:
                await self.async_load_preferences()

            if self._is_access_token_valid():
                _LOGGER.debug("Token still valid, using it")
                return self._prefs[STORAGE_ACCESS_TOKEN]

            if self._is_refresh_token_valid():
                params = {"refreshToken": self._prefs[STORAGE_REFRESH_TOKEN]}
                _LOGGER.debug(
                    "Requesting access token with: %s",
                    json.dumps(params),
                )

                response_json = await self._api_wrapper(
                    path="auth/refresh",
                    method="post",
                    data=params,
                )

                await self._async_update_preferences(
                    response_json["accessToken"],
                    dt_util.parse_datetime(response_json["accessTokenExpirationDate"]),
                    response_json["refreshToken"],
                    dt_util.parse_datetime(response_json["refreshTokenExpirationDate"]),
                )

                return response_json["accessToken"]

            return await self.async_authenticate()

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        default_headers = {
            "Content-type": "application/json; charset=UTF-8",
            "accept": "application/json",
        }

        base_url = "https://public-api.monta.com/api/v1/"

        all_headers = {**default_headers, **(headers or {})}

        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=f"{base_url}{path}",
                    headers=all_headers,
                    json=data,
                )

                _LOGGER.debug("Response header: %s", response.headers)
                _LOGGER.debug("Response status: %s", response.status)

                if response.status in (401, 403):
                    raise MontaApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()

                response_json = await response.json()
                _LOGGER.debug("response body  : %s", response_json)
                return response_json

        except asyncio.TimeoutError as exception:
            raise MontaApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise MontaApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise MontaApiClientError("Something really wrong happened!") from exception

    async def _async_update_preferences(
        self,
        access_token,
        access_token_expiration,
        refresh_token,
        refresh_token_expiration,
    ):
        """Update user preferences."""
        if self._prefs is None:
            await self.async_load_preferences()

        if access_token is not None:
            self._prefs[STORAGE_ACCESS_TOKEN] = access_token
        if access_token_expiration is not None:
            self._prefs[STORAGE_ACCESS_EXPIRE_TIME] = access_token_expiration
        if refresh_token is not None:
            self._prefs[STORAGE_REFRESH_TOKEN] = refresh_token
        if refresh_token_expiration is not None:
            self._prefs[STORAGE_REFRESH_EXPIRE_TIME] = refresh_token_expiration
        await self._store.async_save(self._prefs)

    async def async_load_preferences(self):
        """Load preferences with stored tokens."""
        self._prefs = await self._store.async_load()

        if self._prefs is None:
            self._prefs = {
                STORAGE_ACCESS_TOKEN: None,
                STORAGE_REFRESH_TOKEN: None,
                STORAGE_ACCESS_EXPIRE_TIME: None,
                STORAGE_REFRESH_EXPIRE_TIME: None,
            }

    def _is_access_token_valid(self):
        """Check if a refresh token is already loaded and if it is still valid."""
        if not self._prefs[STORAGE_ACCESS_TOKEN]:
            return False

        if self._prefs[STORAGE_ACCESS_EXPIRE_TIME] is None:
            return False

        expire_time = dt_util.parse_datetime(self._prefs[STORAGE_ACCESS_EXPIRE_TIME])
        preemptive_expire_time = expire_time - timedelta(
            seconds=PREEMPTIVE_REFRESH_TTL_IN_SECONDS
        )

        return dt_util.utcnow() < preemptive_expire_time

    def _is_refresh_token_valid(self):
        """Check if a refresh token is already loaded and if it is still valid."""
        if not self._prefs[STORAGE_REFRESH_TOKEN]:
            return False

        if self._prefs[STORAGE_ACCESS_EXPIRE_TIME] is None:
            return False

        expire_time = dt_util.parse_datetime(self._prefs[STORAGE_REFRESH_EXPIRE_TIME])
        preemptive_expire_time = expire_time - timedelta(
            seconds=PREEMPTIVE_REFRESH_TTL_IN_SECONDS
        )

        return dt_util.utcnow() < preemptive_expire_time
