"""Tests for the Start/Stop switch.

The switch reads on for as long as the charge point holds an open charge
session, whether or not power is flowing. Issue #366: a paused session, or a
car that is full, reports busy-non-charging, and showing that as off invited
the user to start a charge Monta already had, which it refuses with a 412.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.components.switch import SwitchEntityDescription
from pytest_homeassistant.common import MockConfigEntry

from custom_components.monta.const import DOMAIN, ChargerStatus
from custom_components.monta.switch import MontaSwitch

CHARGE_POINT_ID = 1

SESSION_OPEN = {
    ChargerStatus.BUSY,
    ChargerStatus.BUSY_CHARGING,
    ChargerStatus.BUSY_NON_CHARGING,
    ChargerStatus.BUSY_SCHEDULED,
}


def switch_for(state: ChargerStatus) -> MontaSwitch:
    """Return a Start/Stop switch for a charge point in the given state."""
    coordinator = MagicMock()
    coordinator.data = {CHARGE_POINT_ID: SimpleNamespace(state=state)}
    return MontaSwitch(
        coordinator,
        MockConfigEntry(domain=DOMAIN),
        SwitchEntityDescription(key="charger", name="Start/Stop"),
        CHARGE_POINT_ID,
    )


@pytest.mark.parametrize("state", list(ChargerStatus))
def test_switch_is_on_while_a_session_is_open(state: ChargerStatus) -> None:
    """Every charger state is pinned, so a new one has to pick a side."""
    assert switch_for(state).is_on is (state in SESSION_OPEN)
