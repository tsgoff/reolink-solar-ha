"""Config flow for Reolink Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession

from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReolinkCloudAPI
from .const import DOMAIN, CONF_TOTP_SECRET, CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_TOTP_SECRET): str,
        vol.Optional(CONF_STORAGE_PATH, default=DEFAULT_STORAGE_PATH): str,
    }
)


class ReolinkCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reolink Cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate credentials
            session = async_get_clientsession(self.hass)
            api = ReolinkCloudAPI(
                session=session,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                totp_secret=user_input.get(CONF_TOTP_SECRET),
            )

            try:
                if await api.async_login():
                    # Check if already configured
                    await self.async_set_unique_id(user_input[CONF_USERNAME])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Reolink Cloud ({user_input[CONF_USERNAME]})",
                        data=user_input,
                    )
                else:
                    errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "totp_help": "The TOTP secret from your authenticator app (not the 6-digit code)"
            },
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthorization."""
        return await self.async_step_user(user_input)
