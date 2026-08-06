"""Tests for what the integration does when Monta rejects a token.

Covers the two halves of issue #321: an expired access token must not turn
into a request for the user's credentials, and finishing a flow must not set
the entry up twice over the same rotating tokens.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.data_entry_flow import FlowResultType
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


def assert_entry_survived(
    entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Assert the entry came back up with nothing thrown on the way.

    An update listener is what reloads an entry from outside Home Assistant's
    own setup, and such a reload raises out of
    async_config_entry_first_refresh: the coordinators are built with no
    config entry in context. Nobody awaits that task, so the exception only
    reaches the log once it is garbage collected, which is too late to catch
    here reliably. The absence of the listener is the part worth pinning.
    """
    assert entry.state is ConfigEntryState.LOADED
    assert entry.update_listeners == []
    assert [
        record for record in caplog.records if record.levelno >= logging.ERROR
    ] == []


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


async def test_reauth_sets_the_entry_up_once(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    clients: list[FakeMontaClient],
    mock_client: None,  # noqa: ARG001
    mock_credential_check: None,  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Finishing reauthentication reloads the entry exactly once.

    A second, concurrent setup would give the account two clients refreshing
    the same rotating tokens, and whichever refreshed second would be handed
    a 401 an hour later.
    """
    await setup_entry(hass, config_entry)
    assert len(clients) == 1

    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_CLIENT_ID: "new-id", CONF_CLIENT_SECRET: "new-secret"},
    )
    await hass.async_block_till_done()

    assert_entry_survived(config_entry, caplog)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_CLIENT_ID] == "new-id"
    assert len(clients) == 2


async def test_reauth_reloads_even_when_the_credentials_are_unchanged(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    clients: list[FakeMontaClient],
    mock_client: None,  # noqa: ARG001
    mock_credential_check: None,  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Resubmitting the same credentials still reloads the entry.

    The usual reason a user reaches this form is stale tokens, so they will
    often retype what is already configured. Leaving the entry untouched
    would leave it broken with nothing to show for the trip.
    """
    await setup_entry(hass, config_entry)

    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CLIENT_ID: config_entry.data[CONF_CLIENT_ID],
            CONF_CLIENT_SECRET: config_entry.data[CONF_CLIENT_SECRET],
        },
    )
    await hass.async_block_till_done()

    assert_entry_survived(config_entry, caplog)
    assert result["type"] is FlowResultType.ABORT
    assert len(clients) == 2


async def test_options_flow_sets_the_entry_up_once(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    clients: list[FakeMontaClient],
    mock_client: None,  # noqa: ARG001
    mock_credential_check: None,  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Saving the options reloads the entry exactly once.

    New credentials are the case that used to write the entry twice, once for
    the data and once for the options, and so set it up twice.
    """
    await setup_entry(hass, config_entry)
    assert len(clients) == 1

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CLIENT_ID: "new-id",
            CONF_CLIENT_SECRET: "new-secret",
            "scan_interval_charge_points": 300,
            "scan_interval_wallet": 600,
            "scan_interval_transactions": 600,
        },
    )
    await hass.async_block_till_done()

    assert_entry_survived(config_entry, caplog)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.data[CONF_CLIENT_ID] == "new-id"
    assert config_entry.options["scan_interval_charge_points"] == 300
    assert len(clients) == 2
