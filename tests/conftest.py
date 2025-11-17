"""Global fixtures for Monta integration tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from monta import ChargePoint, Wallet, WalletTransaction

from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant

from custom_components.monta.const import (
    CONF_SCAN_INTERVAL_CHARGE_POINTS,
    CONF_SCAN_INTERVAL_WALLET,
    CONF_SCAN_INTERVAL_TRANSACTIONS,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture(name="mock_monta_client")
def mock_monta_client_fixture() -> Generator[MagicMock]:
    """Mock MontaApiClient."""
    with (
        patch(
            "custom_components.monta.config_flow.MontaApiClient", autospec=True
        ) as mock_client,
        patch("custom_components.monta.MontaApiClient", autospec=True),
    ):
        client = mock_client.return_value
        client.async_request_token = AsyncMock(return_value=MagicMock(user_id=123))
        client.async_get_charge_points = AsyncMock(return_value={})
        client.async_get_personal_wallet = AsyncMock(return_value=None)
        client.async_get_wallet_transactions = AsyncMock(return_value=[])
        client.async_get_charges = AsyncMock(return_value=[])
        yield client


@pytest.fixture(name="mock_config_entry")
def mock_config_entry_fixture() -> dict[str, Any]:
    """Mock config entry data."""
    return {
        CONF_CLIENT_ID: "test_client_id",
        CONF_CLIENT_SECRET: "test_client_secret",
        CONF_SCAN_INTERVAL_CHARGE_POINTS: 120,
        CONF_SCAN_INTERVAL_WALLET: 600,
        CONF_SCAN_INTERVAL_TRANSACTIONS: 600,
    }


@pytest.fixture(name="mock_charge_point")
def mock_charge_point_fixture() -> ChargePoint:
    """Mock ChargePoint data."""
    charge_point = MagicMock(spec=ChargePoint)
    charge_point.id = 12345
    charge_point.name = "Test Charger"
    charge_point.brand_name = "Test Brand"
    charge_point.model_name = "Test Model"
    charge_point.firmware_version = "1.0.0"
    charge_point.visibility = "public"
    charge_point.type = "ac"
    charge_point.state = "available"
    charge_point.last_meter_reading_kwh = 100.5
    charge_point.cable_plugged_in = False
    charge_point.charges = []
    return charge_point


@pytest.fixture(name="mock_wallet")
def mock_wallet_fixture() -> Wallet:
    """Mock Wallet data."""
    wallet = MagicMock(spec=Wallet)
    wallet.balance = MagicMock()
    wallet.balance.amount = 50.0
    wallet.balance.credit = 10.0
    wallet.currency = MagicMock()
    wallet.currency.identifier = "usd"
    return wallet


@pytest.fixture(name="mock_wallet_transaction")
def mock_wallet_transaction_fixture() -> WalletTransaction:
    """Mock WalletTransaction data."""
    transaction = MagicMock(spec=WalletTransaction)
    transaction.id = 1
    transaction.state = "complete"
    transaction.to_dict = MagicMock(
        return_value={
            "id": 1,
            "state": "complete",
            "amount": 25.0,
        }
    )
    return transaction


@pytest.fixture(name="setup_integration")
async def setup_integration_fixture(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict[str, Any]
) -> None:
    """Set up the Monta integration in Home Assistant."""
    from homeassistant.config_entries import ConfigEntry

    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Monta account 123",
        data=mock_config_entry,
        source="user",
        unique_id="test_unique_id",
    )

    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return config_entry
