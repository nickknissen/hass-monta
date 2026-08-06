"""Fixtures for the Monta tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from monta import MontaApiClientAuthenticationError
from monta.models import TokenResponse
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.monta.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

CLIENT_ID = "client-id"
CLIENT_SECRET = "client-secret"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,  # noqa: ARG001
) -> None:
    """Load the integration from custom_components."""
    return


class FakeMontaClient:
    """Stands in for MontaApiClient, with its token behaviour.

    Monta hands out access tokens that last an hour and rotates the refresh
    token, so the interesting states are "the cached tokens went stale" and
    "the client id and secret are no longer accepted". They are separate
    switches here because the integration is meant to tell them apart.
    """

    def __init__(self) -> None:
        """Initialize with tokens the API accepts."""
        self.tokens_accepted = True
        self.credentials_accepted = True
        self.authenticate_calls = 0
        self.request_calls = 0

    def expire_tokens(self) -> None:
        """Make the API reject the tokens the client holds."""
        self.tokens_accepted = False

    async def async_authenticate(self) -> None:
        """Mint a token set from the client id and secret."""
        self.authenticate_calls += 1
        if not self.credentials_accepted:
            raise MontaApiClientAuthenticationError("Invalid credentials")
        self.tokens_accepted = True

    def _request(self) -> None:
        self.request_calls += 1
        if not self.tokens_accepted:
            raise MontaApiClientAuthenticationError("Invalid credentials")

    async def async_get_all_charge_points(
        self, per_page: int = 100,  # noqa: ARG002
    ) -> dict[int, Any]:
        """Return no charge points, which keeps the platforms out of it."""
        self._request()
        return {}

    async def async_get_charges(self, *args: Any, **kwargs: Any) -> list[Any]:  # noqa: ANN401, ARG002
        """Return no charges."""
        self._request()
        return []

    async def async_get_personal_wallet(self) -> Any:  # noqa: ANN401
        """Return a wallet."""
        self._request()
        return object()

    async def async_get_wallet_transactions(self) -> list[Any]:
        """Return no transactions."""
        self._request()
        return []


def token_response() -> TokenResponse:
    """Return the token a successful credential check produces."""
    now = datetime.now(UTC)
    return TokenResponse(
        access_token="access",
        access_token_expiration_date=now + timedelta(hours=1),
        refresh_token="refresh",
        refresh_token_expiration_date=now + timedelta(days=31),
        user_id="user-1",
    )


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a configured Monta account."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Monta account user-1",
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    )


@pytest.fixture
def clients() -> list[FakeMontaClient]:
    """Collect every client the integration builds.

    The integration builds exactly one per setup, so the length of this list
    is the number of times the entry has been set up.
    """
    return []


@pytest.fixture
def mock_client(clients: list[FakeMontaClient]):  # noqa: ANN201
    """Patch in the fake client and record each one built."""

    def build(**_: Any) -> FakeMontaClient:
        client = FakeMontaClient()
        clients.append(client)
        return client

    with patch(
        "custom_components.monta.MontaApiClient", side_effect=build,
    ) as mock:
        yield mock


@pytest.fixture
def mock_credential_check():  # noqa: ANN201
    """Accept whatever credentials a config flow validates."""
    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
    ) as mock:
        mock.return_value.async_request_token = AsyncMock(
            return_value=token_response(),
        )
        yield mock
