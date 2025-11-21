"""Adds config flow for Monta."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.storage import Store
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
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .storage import HomeAssistantTokenStorage

if TYPE_CHECKING:
    from monta.models import TokenResponse


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

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,  # noqa: ARG004
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return MontaOptionsFlowHandler()

    async def _test_credentials(
        self, client_id: str, client_secret: str,
    ) -> TokenResponse:
        """Validate credentials."""
        client = MontaApiClient(
            client_id=client_id,
            client_secret=client_secret,
            session=async_create_clientsession(self.hass),
            token_storage=HomeAssistantTokenStorage(
                Store(self.hass, STORAGE_VERSION, STORAGE_KEY),
            ),
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
            # Only validate credentials if they were changed
            if user_input.get(CONF_CLIENT_ID) != self.config_entry.data.get(
                CONF_CLIENT_ID,
            ) or user_input.get(CONF_CLIENT_SECRET) != self.config_entry.data.get(
                CONF_CLIENT_SECRET,
            ):
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
                # Update the config entry data with new credentials if they changed
                if user_input.get(CONF_CLIENT_ID) != self.config_entry.data.get(
                    CONF_CLIENT_ID,
                ) or user_input.get(CONF_CLIENT_SECRET) != self.config_entry.data.get(
                    CONF_CLIENT_SECRET,
                ):
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
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
                return self.async_create_entry(title="", data=user_input)

        # Build defaults from user_input -> options -> data
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
        client = MontaApiClient(
            client_id=client_id,
            client_secret=client_secret,
            session=async_create_clientsession(self.hass),
            token_storage=HomeAssistantTokenStorage(
                Store(self.hass, STORAGE_VERSION, STORAGE_KEY),
            ),
        )
        return await client.async_request_token()
