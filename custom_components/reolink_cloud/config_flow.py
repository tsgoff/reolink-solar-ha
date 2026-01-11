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
from .const import DOMAIN, CONF_MFA_CODE, CONF_MFA_TRUST_TOKEN, CONF_STORAGE_PATH, DEFAULT_STORAGE_PATH

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_MFA_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MFA_CODE): str,
    }
)


class ReolinkCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reolink Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._username: str | None = None
        self._password: str | None = None
        self._api: ReolinkCloudAPI | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - username and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            
            # Create API instance
            session = async_get_clientsession(self.hass)
            self._api = ReolinkCloudAPI(
                session=session,
                username=self._username,
                password=self._password,
            )
            
            # Move to MFA step
            return await self.async_step_mfa()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the MFA step - 6-digit code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mfa_code = user_input[CONF_MFA_CODE]
            
            # Try to login with MFA code
            success, mfa_trust_token = await self._api.async_login_with_mfa_code(mfa_code)
            
            if success:
                # Check if already configured
                await self.async_set_unique_id(self._username)
                self._abort_if_unique_id_configured()

                # Store credentials and MFA trust token
                return self.async_create_entry(
                    title=f"Reolink Cloud ({self._username})",
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                        CONF_MFA_TRUST_TOKEN: mfa_trust_token,
                        CONF_STORAGE_PATH: DEFAULT_STORAGE_PATH,
                    },
                )
            else:
                errors["base"] = "invalid_mfa_code"

        return self.async_show_form(
            step_id="mfa",
            data_schema=STEP_MFA_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "username": self._username,
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauthorization when MFA trust token expires."""
        self._username = entry_data.get(CONF_USERNAME)
        self._password = entry_data.get(CONF_PASSWORD)
        
        session = async_get_clientsession(self.hass)
        self._api = ReolinkCloudAPI(
            session=session,
            username=self._username,
            password=self._password,
        )
        
        return await self.async_step_reauth_mfa()

    async def async_step_reauth_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle MFA during reauth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mfa_code = user_input[CONF_MFA_CODE]
            
            success, mfa_trust_token = await self._api.async_login_with_mfa_code(mfa_code)
            
            if success and mfa_trust_token:
                # Update the existing entry with new MFA trust token
                existing_entry = await self.async_set_unique_id(self._username)
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={
                            **existing_entry.data,
                            CONF_MFA_TRUST_TOKEN: mfa_trust_token,
                        },
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
            else:
                errors["base"] = "invalid_mfa_code"

        return self.async_show_form(
            step_id="reauth_mfa",
            data_schema=STEP_MFA_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "username": self._username,
            },
        )
