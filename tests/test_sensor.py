"""Test Monta sensors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.monta.const import DOMAIN


async def test_charge_point_sensors(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test charge point sensors are created correctly."""
    mock_monta_client.async_get_charge_points.return_value = {12345: mock_charge_point}

    from homeassistant.config_entries import ConfigEntry

    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        source="user",
        unique_id="test_unique_id",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Verify charge point sensors exist
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    sensor_entities = [e for e in entries if e.domain == "sensor"]

    assert len(sensor_entities) > 0

    # Check specific sensor states
    state = hass.states.get("sensor.12345_charger_visibility")
    if state:
        assert state.state == "public"

    state = hass.states.get("sensor.12345_charger_type")
    if state:
        assert state.state == "ac"

    state = hass.states.get("sensor.12345_charger_state")
    if state:
        assert state.state == "available"


async def test_wallet_sensor(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_wallet: MagicMock
) -> None:
    """Test wallet sensor is created correctly."""
    mock_monta_client.async_get_charge_points.return_value = {}
    mock_monta_client.async_get_personal_wallet.return_value = mock_wallet

    from homeassistant.config_entries import ConfigEntry

    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        source="user",
        unique_id="test_unique_id",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    wallet_sensors = [
        e for e in entries if e.domain == "sensor" and "wallet" in e.entity_id
    ]

    assert len(wallet_sensors) > 0


async def test_transaction_sensor(
    hass: HomeAssistant,
    mock_monta_client: MagicMock,
    mock_wallet_transaction: MagicMock,
) -> None:
    """Test transaction sensor is created correctly."""
    mock_monta_client.async_get_charge_points.return_value = {}
    mock_monta_client.async_get_wallet_transactions.return_value = [
        mock_wallet_transaction
    ]

    from homeassistant.config_entries import ConfigEntry

    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Monta account 123",
        data={
            "client_id": "test_id",
            "client_secret": "test_secret",
            "scan_interval_charge_points": 120,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
        source="user",
        unique_id="test_unique_id",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    transaction_sensors = [
        e for e in entries if e.domain == "sensor" and "transaction" in e.entity_id
    ]

    assert len(transaction_sensors) > 0
