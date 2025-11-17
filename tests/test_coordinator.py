"""Test Monta coordinators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from monta import (
    MontaApiClientAuthenticationError,
    MontaApiClientError,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.monta.const import DOMAIN
from custom_components.monta.coordinator import (
    MontaChargePointCoordinator,
    MontaWalletCoordinator,
    MontaTransactionCoordinator,
)


async def test_charge_point_coordinator_update_success(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test successful charge point coordinator update."""
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaChargePointCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=120, config_entry=config_entry
    )

    await coordinator.async_refresh()

    assert coordinator.data == {12345: mock_charge_point}
    mock_monta_client.async_get_charge_points.assert_called_once()


async def test_charge_point_coordinator_auth_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test charge point coordinator handles authentication errors."""
    mock_monta_client.async_get_charge_points.side_effect = (
        MontaApiClientAuthenticationError("Auth failed")
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaChargePointCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=120, config_entry=config_entry
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_refresh()


async def test_charge_point_coordinator_api_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test charge point coordinator handles API errors."""
    mock_monta_client.async_get_charge_points.side_effect = MontaApiClientError(
        "API error"
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaChargePointCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=120, config_entry=config_entry
    )

    with pytest.raises(UpdateFailed):
        await coordinator.async_refresh()


async def test_wallet_coordinator_update_success(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_wallet: MagicMock
) -> None:
    """Test successful wallet coordinator update."""
    mock_monta_client.async_get_personal_wallet.return_value = mock_wallet

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaWalletCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=600, config_entry=config_entry
    )

    await coordinator.async_refresh()

    assert coordinator.data == mock_wallet
    mock_monta_client.async_get_personal_wallet.assert_called_once()


async def test_wallet_coordinator_auth_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test wallet coordinator handles authentication errors."""
    mock_monta_client.async_get_personal_wallet.side_effect = (
        MontaApiClientAuthenticationError("Auth failed")
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaWalletCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=600, config_entry=config_entry
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_refresh()


async def test_transaction_coordinator_update_success(
    hass: HomeAssistant,
    mock_monta_client: MagicMock,
    mock_wallet_transaction: MagicMock,
) -> None:
    """Test successful transaction coordinator update."""
    mock_monta_client.async_get_wallet_transactions.return_value = [
        mock_wallet_transaction
    ]

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaTransactionCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=600, config_entry=config_entry
    )

    await coordinator.async_refresh()

    assert coordinator.data == [mock_wallet_transaction]
    mock_monta_client.async_get_wallet_transactions.assert_called_once()


async def test_transaction_coordinator_auth_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test transaction coordinator handles authentication errors."""
    mock_monta_client.async_get_wallet_transactions.side_effect = (
        MontaApiClientAuthenticationError("Auth failed")
    )

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    config_entry.add_to_hass(hass)
    coordinator = MontaTransactionCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=600, config_entry=config_entry
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_refresh()


async def test_charge_point_start_charge(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test starting a charge."""
    mock_monta_client.async_start_charge = AsyncMock()
    mock_monta_client.async_get_charge_points.return_value = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    coordinator = MontaChargePointCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=120, config_entry=config_entry
    )

    await coordinator.async_start_charge(12345)

    mock_monta_client.async_start_charge.assert_called_once_with(12345)


async def test_charge_point_stop_charge(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test stopping a charge."""
    mock_charge = MagicMock()
    mock_charge.id = 999
    mock_monta_client.async_get_charges = AsyncMock(return_value=[mock_charge])
    mock_monta_client.async_stop_charge = AsyncMock()
    mock_monta_client.async_get_charge_points.return_value = {}

    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    coordinator = MontaChargePointCoordinator(
        hass=hass, client=mock_monta_client, scan_interval=120, config_entry=config_entry
    )

    await coordinator.async_stop_charge(12345)

    mock_monta_client.async_get_charges.assert_called_once_with(12345)
    mock_monta_client.async_stop_charge.assert_called_once_with(999)
