"""Config flow for Reolink Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReolinkCloudAPI
from .const import DOMAIN, CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ReolinkCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reolink Cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - username and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            
            # Create API instance and try to login
            session = async_get_clientsession(self.hass)
            api = ReolinkCloudAPI(
                session=session,
                username=username,
                password=password,
            )
            
            if await api.async_login():
                # Check if already configured
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                # Store credentials
                return self.async_create_entry(
                    title=f"Reolink Cloud ({username})",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_STORAGE_PATH: DEFAULT_STORAGE_PATH,
                    },
                )
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauthorization."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            
            session = async_get_clientsession(self.hass)
            api = ReolinkCloudAPI(
                session=session,
                username=username,
                password=password,
            )
            
            if await api.async_login():
                existing_entry = await self.async_set_unique_id(username)
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_STORAGE_PATH: existing_entry.data.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH),
                        },
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
