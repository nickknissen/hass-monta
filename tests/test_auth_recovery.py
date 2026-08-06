"""Tests for what the integration does when Monta rejects a token.

Covers the first half of issue #321: an expired access token must not turn
into a request for the user's credentials.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from monta import MontaApiClientAuthenticationError

from custom_components.monta.const import DOMAIN
from custom_components.monta.coordinator import (
    MontaAuthGuard,
    MontaChargePointCoordinator,
)

if TYPE_CHECKING:
    from typing import Any

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from .conftest import FakeMontaClient


@pytest.fixture(autouse=True)
def no_platforms():  # noqa: ANN201
    """Keep the entities out of these tests, they are about the entry."""
    with patch("custom_components.monta.PLATFORMS", []):
        yield


def reauth_flows(hass: HomeAssistant) -> list[dict]:
    """Return the reauthentication flows waiting for the user."""
    return [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["context"].get("source") == SOURCE_REAUTH
    ]


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up a config entry and wait for it to settle."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_expired_tokens_recover_without_asking_the_user(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    clients: list[FakeMontaClient],
    mock_client: None,  # noqa: ARG001
) -> None:
    """An expired access token is replaced from the configured credentials.

    Monta access tokens last an hour. Expiry says nothing about the client id
    and secret, so it must not surface as "your credentials are no longer
    valid" once an hour, which is what issue #321 reports.
    """
    await setup_entry(hass, config_entry)
    client = clients[0]

    client.expire_tokens()
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["charge_point"]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success
    assert client.authenticate_calls == 1
    assert config_entry.state is ConfigEntryState.LOADED
    assert reauth_flows(hass) == []


async def test_expired_tokens_are_replaced_once_for_all_coordinators(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    clients: list[FakeMontaClient],
    mock_client: None,  # noqa: ARG001
) -> None:
    """The three coordinators share a client, so they share one new token set.

    Letting each of them authenticate on its own would have them rotating the
    tokens out from under each other.
    """
    await setup_entry(hass, config_entry)
    client = clients[0]
    coordinators = hass.data[DOMAIN][config_entry.entry_id]

    client.expire_tokens()
    for coordinator in coordinators.values():
        await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert all(
        coordinator.last_update_success for coordinator in coordinators.values()
    )
    assert client.authenticate_calls == 1


async def test_rejected_credentials_do_ask_the_user(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    clients: list[FakeMontaClient],
    mock_client: None,  # noqa: ARG001
) -> None:
    """Credentials the API itself refuses are worth interrupting the user for."""
    await setup_entry(hass, config_entry)
    client = clients[0]

    client.expire_tokens()
    client.credentials_accepted = False
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["charge_point"]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert len(reauth_flows(hass)) == 1


class BackfilledChargePoint:
    """A charge point as the coordinator handles it: a bag of charges."""

    def __init__(self) -> None:
        """Initialize with no charges, as the API returns it."""
        self.charges: list[Any] = []


class BackfillClient:
    """A client whose bulk batch never covers its charge points.

    Both charge points therefore need a targeted fetch, and the second of
    those is refused, which is what sends the whole update through the retry.
    """

    def __init__(self) -> None:
        """Initialize with the second targeted fetch set to be refused."""
        self.targeted: list[int] = []
        self._refuse_targeted = True

    async def async_authenticate(self) -> None:
        """Mint a token set the API accepts."""

    async def async_get_all_charge_points(
        self, per_page: int = 100,  # noqa: ARG002
    ) -> dict[int, BackfilledChargePoint]:
        """Return two charge points, neither of them in the bulk batch."""
        return {1: BackfilledChargePoint(), 2: BackfilledChargePoint()}

    async def async_get_charges(
        self,
        charge_point_id: int | None = None,
        per_page: int | None = None,  # noqa: ARG002
    ) -> list[Any]:
        """Return an empty bulk batch, or a charge for a targeted fetch."""
        if charge_point_id is None:
            return []
        self.targeted.append(charge_point_id)
        if charge_point_id == 2 and self._refuse_targeted:
            self._refuse_targeted = False
            raise MontaApiClientAuthenticationError("Invalid credentials")
        return [object()]


async def test_a_refused_backfill_does_not_strand_the_chargers_before_it(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Chargers backfilled before a 401 are backfilled again on the retry.

    Re-minting the token runs the whole update again, so anything the
    abandoned attempt recorded as backfilled would be taken for done the
    second time round and keep the empty charges it was left with.
    """
    config_entry.add_to_hass(hass)
    client = BackfillClient()
    coordinator = MontaChargePointCoordinator(
        hass=hass,
        entry=config_entry,
        client=client,
        auth=MontaAuthGuard(client),
        scan_interval=300,
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert client.targeted == [1, 2, 1, 2]
    assert coordinator.data[1].charges
    assert coordinator.data[2].charges
