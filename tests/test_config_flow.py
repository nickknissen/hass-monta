"""Test Monta config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from monta import (
    MontaApiClientAuthenticationError,
    MontaApiClientCommunicationError,
    MontaApiClientError,
)

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.monta.const import (
    CONF_SCAN_INTERVAL_CHARGE_POINTS,
    CONF_SCAN_INTERVAL_WALLET,
    CONF_SCAN_INTERVAL_TRANSACTIONS,
    DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
    DEFAULT_SCAN_INTERVAL_WALLET,
    DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
    DOMAIN,
)


async def test_user_flow_success(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "test_client_secret",
                CONF_SCAN_INTERVAL_CHARGE_POINTS: DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
                CONF_SCAN_INTERVAL_WALLET: DEFAULT_SCAN_INTERVAL_WALLET,
                CONF_SCAN_INTERVAL_TRANSACTIONS: DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Monta account 123"
    assert result["data"][CONF_CLIENT_ID] == "test_client_id"
    assert result["data"][CONF_CLIENT_SECRET] == "test_client_secret"


async def test_user_flow_authentication_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test user flow with authentication error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_monta_client.async_request_token.side_effect = (
        MontaApiClientAuthenticationError("Invalid credentials")
    )

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "wrong_secret",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}


async def test_user_flow_communication_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test user flow with communication error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_monta_client.async_request_token.side_effect = (
        MontaApiClientCommunicationError("Connection failed")
    )

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "test_secret",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "connection"}


async def test_user_flow_unknown_error(
    hass: HomeAssistant, mock_monta_client: MagicMock
) -> None:
    """Test user flow with unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_monta_client.async_request_token.side_effect = MontaApiClientError(
        "Unknown error"
    )

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "test_secret",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_options_flow_success(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict
) -> None:
    """Test successful options flow."""
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

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "test_client_id",
                CONF_CLIENT_SECRET: "test_client_secret",
                CONF_SCAN_INTERVAL_CHARGE_POINTS: 180,
                CONF_SCAN_INTERVAL_WALLET: 300,
                CONF_SCAN_INTERVAL_TRANSACTIONS: 300,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_credential_change(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict
) -> None:
    """Test options flow with credential changes."""
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

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "new_client_id",
                CONF_CLIENT_SECRET: "new_client_secret",
                CONF_SCAN_INTERVAL_CHARGE_POINTS: 120,
                CONF_SCAN_INTERVAL_WALLET: 600,
                CONF_SCAN_INTERVAL_TRANSACTIONS: 600,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    mock_monta_client.async_request_token.assert_called_once()


async def test_options_flow_authentication_error(
    hass: HomeAssistant, mock_monta_client: MagicMock, mock_config_entry: dict
) -> None:
    """Test options flow with authentication error when changing credentials."""
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

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    mock_monta_client.async_request_token.side_effect = (
        MontaApiClientAuthenticationError("Invalid credentials")
    )

    with patch(
        "custom_components.monta.config_flow.MontaApiClient",
        return_value=mock_monta_client,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_CLIENT_ID: "new_client_id",
                CONF_CLIENT_SECRET: "wrong_secret",
                CONF_SCAN_INTERVAL_CHARGE_POINTS: 120,
                CONF_SCAN_INTERVAL_WALLET: 600,
                CONF_SCAN_INTERVAL_TRANSACTIONS: 600,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}
