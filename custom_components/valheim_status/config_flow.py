"""Config flow for Valheim Server Status."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_PATH,
    CONF_SCAN_INTERVAL,
    CONF_STALE_AFTER,
    DEFAULT_NAME,
    DEFAULT_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STALE_AFTER,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .coordinator import CannotConnect, InvalidResponse, build_url, fetch_status

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): cv.port,
            vol.Required(CONF_PATH, default=defaults.get(CONF_PATH, DEFAULT_PATH)): str,
            vol.Required(CONF_SSL, default=defaults.get(CONF_SSL, False)): bool,
            vol.Required(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, True)
            ): bool,
        }
    )


class ValheimStatusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the host serving status.json and check it answers."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            url = build_url(user_input)
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            session = async_get_clientsession(
                self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]
            )
            try:
                await fetch_status(session, url)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error fetching %s", url)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return ValheimStatusOptionsFlow()


class ValheimStatusOptionsFlow(OptionsFlow):
    """Poll interval and staleness threshold."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                    vol.Required(
                        CONF_STALE_AFTER,
                        default=opts.get(CONF_STALE_AFTER, DEFAULT_STALE_AFTER),
                    ): vol.All(vol.Coerce(int), vol.Range(min=15)),
                }
            ),
        )
