"""Test Monta switches."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.monta.const import DOMAIN, ChargerStatus


async def test_switch_turn_on(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test turning on the switch."""
    mock_charge_point.state = ChargerStatus.AVAILABLE
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}
    mock_monta_client.async_start_charge = AsyncMock()

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    # Turn on the switch
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_on",
        {"entity_id": "switch.12345_charger"},
        blocking=True,
    )

    mock_monta_client.async_start_charge.assert_called_once_with(12345)


async def test_switch_turn_off(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test turning off the switch."""
    mock_charge_point.state = ChargerStatus.BUSY_CHARGING
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}
    mock_monta_client.async_stop_charge = AsyncMock()
    mock_monta_client.async_get_charges = AsyncMock(return_value=[MagicMock(id=999)])

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    # Turn off the switch
    await hass.services.async_call(
        SWITCH_DOMAIN,
        "turn_off",
        {"entity_id": "switch.12345_charger"},
        blocking=True,
    )

    mock_monta_client.async_get_charges.assert_called_with(12345)
    mock_monta_client.async_stop_charge.assert_called_once_with(999)


async def test_switch_is_on_when_charging(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test switch is on when charger is charging."""
    mock_charge_point.state = ChargerStatus.BUSY_CHARGING
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.12345_charger")
    assert state is not None
    assert state.state == STATE_ON


async def test_switch_is_off_when_available(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test switch is off when charger is available."""
    mock_charge_point.state = ChargerStatus.AVAILABLE
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.12345_charger")
    assert state is not None
    assert state.state == STATE_OFF


async def test_switch_unavailable_when_disconnected(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test switch is unavailable when charger is disconnected."""
    mock_charge_point.state = ChargerStatus.DISCONNECTED
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.12345_charger")
    assert state is not None
    assert state.state == "unavailable"


async def test_switch_unavailable_when_error(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test switch is unavailable when charger has error."""
    mock_charge_point.state = ChargerStatus.ERROR
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("switch.12345_charger")
    assert state is not None
    assert state.state == "unavailable"
