"""Test Monta integration initialization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.monta.const import DOMAIN


async def test_setup_entry_success(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict
) -> None:
    """Test successful setup of a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data=mock_config_entry,
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]


async def test_unload_entry(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict
) -> None:
    """Test unloading a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data=mock_config_entry,
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_reload_entry(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict
) -> None:
    """Test reloading a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Monta account 123",
        data=mock_config_entry,
        unique_id="test_unique_id",
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.monta.MontaApiClient", return_value=mock_monta_client
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED
