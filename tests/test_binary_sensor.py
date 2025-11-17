"""Test Monta binary sensors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.monta.const import DOMAIN


async def test_binary_sensor_cable_plugged_in_false(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test binary sensor when cable is not plugged in."""
    mock_charge_point.cable_plugged_in = False
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
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.12345_cable_plugged_in")
    assert state is not None
    assert state.state == "off"


async def test_binary_sensor_cable_plugged_in_true(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test binary sensor when cable is plugged in."""
    mock_charge_point.cable_plugged_in = True
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
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.12345_cable_plugged_in")
    assert state is not None
    assert state.state == "on"


async def test_binary_sensor_entity_registry(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_charge_point: MagicMock
) -> None:
    """Test binary sensor is registered in entity registry."""
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
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    binary_sensor_entities = [e for e in entries if e.domain == "binary_sensor"]

    assert len(binary_sensor_entities) > 0
