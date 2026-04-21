"""Config flow for Jellyfin Browser."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import JellyfinApiError, JellyfinClient
from .const import (
    CONF_API_KEY,
    CONF_SERVER_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the config schema."""
    values = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_SERVER_URL, default=values.get(CONF_SERVER_URL, "")): str,
            vol.Required(CONF_API_KEY, default=values.get(CONF_API_KEY, "")): str,
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=values.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
        }
    )


async def _async_validate_input(hass, data: dict[str, Any]) -> dict[str, str]:
    """Validate the provided server settings."""
    client = JellyfinClient(
        data[CONF_SERVER_URL],
        data[CONF_API_KEY],
        async_create_clientsession(hass),
    )
    info = await client.async_get_public_info()
    return {
        "title": info.get("ServerName") or DEFAULT_NAME,
    }


class JellyfinBrowserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jellyfin Browser."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERVER_URL].rstrip("/").lower())
            self._abort_if_unique_id_configured()

            try:
                info = await _async_validate_input(self.hass, user_input)
            except JellyfinApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pragma: no cover - defensive guard for HA runtime
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema(user_input), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow."""
        return JellyfinBrowserOptionsFlow(config_entry)


class JellyfinBrowserOptionsFlow(config_entries.OptionsFlow):
    """Manage Jellyfin Browser options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data={CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL]})

        defaults = {
            CONF_SERVER_URL: self._entry.data[CONF_SERVER_URL],
            CONF_API_KEY: self._entry.data[CONF_API_KEY],
            CONF_UPDATE_INTERVAL: self._entry.options.get(
                CONF_UPDATE_INTERVAL,
                self._entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ),
        }
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=defaults[CONF_UPDATE_INTERVAL],
                ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
