"""Adds config flow for Monta."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_SECRET, CONF_CLIENT_ID
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.storage import Store

from .api import (
    MontaApiClient,
    MontaApiClientAuthenticationError,
    MontaApiClientCommunicationError,
    MontaApiClientError,
)
from .const import DOMAIN, LOGGER, STORAGE_KEY, STORAGE_VERSION


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
                    title=f"Monta account {response['userId']}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CLIENT_ID,
                        default=(user_input or {}).get(CONF_CLIENT_ID),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_CLIENT_SECRET): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(self, client_id: str, client_secret: str) -> any:
        """Validate credentials."""
        client = MontaApiClient(
            client_id=client_id,
            client_secret=client_secret,
            session=async_create_clientsession(self.hass),
            store=Store(self.hass, STORAGE_VERSION, STORAGE_KEY),
        )
        return await client.async_request_token()
