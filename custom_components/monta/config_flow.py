"""Adds config flow for Monta."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from monta import (
    MontaApiClient,
    MontaApiClientAuthenticationError,
    MontaApiClientCommunicationError,
    MontaApiClientError,
)

from .const import (
    CONF_SCAN_INTERVAL_CHARGE_POINTS,
    CONF_SCAN_INTERVAL_TRANSACTIONS,
    CONF_SCAN_INTERVAL_WALLET,
    DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
    DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
    DEFAULT_SCAN_INTERVAL_WALLET,
    DOMAIN,
    LOGGER,
)
from .storage import async_get_token_store

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from monta.models import TokenResponse


def build_credentials_schema(defaults: dict) -> vol.Schema:
    """Build a schema asking only for credentials, as reauthentication does."""
    return vol.Schema(
        {
            vol.Required(
                CONF_CLIENT_ID,
                default=defaults.get(CONF_CLIENT_ID),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
            vol.Required(CONF_CLIENT_SECRET): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
        },
    )


def build_schema(defaults: dict) -> vol.Schema:
    """Build the configuration schema with provided defaults."""
    return vol.Schema(
        {
            vol.Required(
                CONF_CLIENT_ID,
                default=defaults.get(CONF_CLIENT_ID),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
            vol.Required(
                CONF_CLIENT_SECRET,
                default=defaults.get(CONF_CLIENT_SECRET),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_CHARGE_POINTS,
                default=defaults.get(
                    CONF_SCAN_INTERVAL_CHARGE_POINTS,
                    DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=3600,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_WALLET,
                default=defaults.get(
                    CONF_SCAN_INTERVAL_WALLET,
                    DEFAULT_SCAN_INTERVAL_WALLET,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=7200,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL_TRANSACTIONS,
                default=defaults.get(
                    CONF_SCAN_INTERVAL_TRANSACTIONS,
                    DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=7200,
                    unit_of_measurement="seconds",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        },
    )


class MontaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Monta."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                response = await self._test_credentials(
                    client_id=user_input[CONF_CLIENT_ID],
                    client_secret=user_input[CONF_CLIENT_SECRET],
                )
            except MontaApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except MontaApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except MontaApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Monta account {response.user_id}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema(user_input or {}),
            errors=_errors,
        )

    async def async_step_reauth(
        self,
        _entry_data: Mapping[str, Any],
    ) -> config_entries.FlowResult:
        """Handle credentials the API has stopped accepting.

        Reached whenever a coordinator turns a 401 into ConfigEntryAuthFailed,
        which makes Home Assistant start a reauth flow for the entry.
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Ask for working credentials and put them on the existing entry."""
        entry = self._get_reauth_entry()
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    client_id=user_input[CONF_CLIENT_ID],
                    client_secret=user_input[CONF_CLIENT_SECRET],
                )
            except MontaApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except MontaApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except MontaApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Whatever is cached was minted for the old credentials.
                await async_get_token_store(
                    self.hass, entry.entry_id,
                ).async_remove()
                # Reloads even when the credentials came back unchanged,
                # which is the common case: it is usually the cached tokens
                # that went bad, not the client id and secret.
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=build_credentials_schema(
                {CONF_CLIENT_ID: entry.data.get(CONF_CLIENT_ID)},
            ),
            errors=_errors,
        )

    @staticmethod
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return MontaOptionsFlowHandler()

    async def _test_credentials(
        self, client_id: str, client_secret: str,
    ) -> TokenResponse:
        """Validate credentials."""
        # No token storage: requesting a token here must not touch the tokens
        # cached for an existing entry.
        client = MontaApiClient(
            client_id=client_id,
            client_secret=client_secret,
            session=async_create_clientsession(self.hass),
        )
        return await client.async_request_token()


class MontaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Monta."""

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Manage the options."""
        _errors = {}
        if user_input is not None:
            credentials_changed = user_input.get(
                CONF_CLIENT_ID,
            ) != self.config_entry.data.get(CONF_CLIENT_ID) or user_input.get(
                CONF_CLIENT_SECRET,
            ) != self.config_entry.data.get(CONF_CLIENT_SECRET)

            if credentials_changed:
                try:
                    await self._test_credentials(
                        client_id=user_input[CONF_CLIENT_ID],
                        client_secret=user_input[CONF_CLIENT_SECRET],
                    )
                except MontaApiClientAuthenticationError as exception:
                    LOGGER.warning(exception)
                    _errors["base"] = "auth"
                except MontaApiClientCommunicationError as exception:
                    LOGGER.error(exception)
                    _errors["base"] = "connection"
                except MontaApiClientError as exception:
                    LOGGER.exception(exception)
                    _errors["base"] = "unknown"

            if not _errors:
                if credentials_changed:
                    # Drop the cached tokens before the entry reloads with the
                    # new credentials, they belong to the old ones.
                    await async_get_token_store(
                        self.hass, self.config_entry.entry_id,
                    ).async_remove()
                # Data and options are written together, and the reload is
                # asked for here rather than from an update listener: pairing
                # a listener with a flow that reloads is deprecated in Home
                # Assistant, and set the entry up twice. Writing the options
                # now also leaves async_create_entry below nothing to change.
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=user_input,
                    data={
                        CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                        CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET],
                        CONF_SCAN_INTERVAL_CHARGE_POINTS: user_input.get(
                            CONF_SCAN_INTERVAL_CHARGE_POINTS,
                            DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
                        ),
                        CONF_SCAN_INTERVAL_WALLET: user_input.get(
                            CONF_SCAN_INTERVAL_WALLET,
                            DEFAULT_SCAN_INTERVAL_WALLET,
                        ),
                        CONF_SCAN_INTERVAL_TRANSACTIONS: user_input.get(
                            CONF_SCAN_INTERVAL_TRANSACTIONS,
                            DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
                        ),
                    },
                )
                self.hass.config_entries.async_schedule_reload(
                    self.config_entry.entry_id,
                )
                return self.async_create_entry(title="", data=user_input)

        # Credentials are shown back as they were typed, since this form
        # re-renders when the check on them fails. The intervals are read
        # from what is saved: options first, then the entry's data.
        defaults = {
            CONF_CLIENT_ID: (user_input or {}).get(
                CONF_CLIENT_ID,
                self.config_entry.data.get(CONF_CLIENT_ID),
            ),
            CONF_CLIENT_SECRET: (user_input or {}).get(
                CONF_CLIENT_SECRET,
                self.config_entry.data.get(CONF_CLIENT_SECRET),
            ),
            CONF_SCAN_INTERVAL_CHARGE_POINTS: self.config_entry.options.get(
                CONF_SCAN_INTERVAL_CHARGE_POINTS,
                self.config_entry.data.get(
                    CONF_SCAN_INTERVAL_CHARGE_POINTS,
                    DEFAULT_SCAN_INTERVAL_CHARGE_POINTS,
                ),
            ),
            CONF_SCAN_INTERVAL_WALLET: self.config_entry.options.get(
                CONF_SCAN_INTERVAL_WALLET,
                self.config_entry.data.get(
                    CONF_SCAN_INTERVAL_WALLET,
                    DEFAULT_SCAN_INTERVAL_WALLET,
                ),
            ),
            CONF_SCAN_INTERVAL_TRANSACTIONS: self.config_entry.options.get(
                CONF_SCAN_INTERVAL_TRANSACTIONS,
                self.config_entry.data.get(
                    CONF_SCAN_INTERVAL_TRANSACTIONS,
                    DEFAULT_SCAN_INTERVAL_TRANSACTIONS,
                ),
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(defaults),
            errors=_errors,
        )

    async def _test_credentials(
        self, client_id: str, client_secret: str,
    ) -> TokenResponse:
        """Validate credentials."""
        # No token storage: validating here must not overwrite the tokens
        # cached for this entry, which still belong to the old credentials.
        client = MontaApiClient(
            client_id=client_id,
            client_secret=client_secret,
            session=async_create_clientsession(self.hass),
        )
        return await client.async_request_token()
