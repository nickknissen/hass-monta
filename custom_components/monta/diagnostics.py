"""Diagnostics support for Monta."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    This function provides diagnostic information about the Monta integration
    for troubleshooting and debugging purposes. Sensitive information like
    client secrets and tokens are excluded.
    """
    coordinators = hass.data[DOMAIN][entry.entry_id]
    charge_point_coordinator = coordinators["charge_point"]
    wallet_coordinator = coordinators["wallet"]
    transaction_coordinator = coordinators["transaction"]

    # Collect diagnostic data from coordinators
    diagnostics_data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "version": entry.version,
        },
        "coordinators": {
            "charge_point": {
                "last_update_success": charge_point_coordinator.last_update_success,
                "update_interval": str(charge_point_coordinator.update_interval),
                "data_available": charge_point_coordinator.data is not None,
                "charge_points_count": (
                    len(charge_point_coordinator.data)
                    if charge_point_coordinator.data
                    else 0
                ),
            },
            "wallet": {
                "last_update_success": wallet_coordinator.last_update_success,
                "update_interval": str(wallet_coordinator.update_interval),
                "data_available": wallet_coordinator.data is not None,
            },
            "transaction": {
                "last_update_success": transaction_coordinator.last_update_success,
                "update_interval": str(transaction_coordinator.update_interval),
                "data_available": transaction_coordinator.data is not None,
                "transactions_count": (
                    len(transaction_coordinator.data)
                    if transaction_coordinator.data
                    else 0
                ),
            },
        },
    }

    # Add charge point details (without sensitive information)
    if charge_point_coordinator.data:
        charge_points_info = []
        for charge_point_id, charge_point in charge_point_coordinator.data.items():
            charge_point_info = {
                "id": charge_point_id,
                "name": charge_point.name,
                "state": charge_point.state,
                "visibility": charge_point.visibility,
                "type": charge_point.type,
                "brand_name": charge_point.brand_name,
                "model_name": charge_point.model_name,
                "firmware_version": charge_point.firmware_version,
                "cable_plugged_in": charge_point.cable_plugged_in,
                "last_meter_reading_kwh": charge_point.last_meter_reading_kwh,
                "charges_count": len(charge_point.charges) if charge_point.charges else 0,
            }
            charge_points_info.append(charge_point_info)
        diagnostics_data["charge_points"] = charge_points_info

    # Add wallet information (without sensitive financial details)
    if wallet_coordinator.data:
        diagnostics_data["wallet"] = {
            "has_balance": wallet_coordinator.data.balance is not None,
            "currency": (
                wallet_coordinator.data.currency.identifier
                if wallet_coordinator.data.currency
                else None
            ),
        }

    # Add transaction information (count only, no sensitive details)
    if transaction_coordinator.data:
        diagnostics_data["transactions"] = {
            "count": len(transaction_coordinator.data),
            "states": [tx.state for tx in transaction_coordinator.data],
        }

    return diagnostics_data
