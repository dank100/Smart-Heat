"""Config flow for Wavin Smart Heat."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_APPLY_CHANGES,
    CONF_AREA_ID,
    CONF_CLIMATE_ENTITY,
    CONF_DAY_START,
    CONF_DAY_TEMP,
    CONF_EXTRA_SENSORS,
    CONF_LEARNING_RATE,
    CONF_LIGHT_ENTITIES,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_MORNING_TEMP,
    CONF_MORNING_TIME,
    CONF_NIGHT_START,
    CONF_NIGHT_TEMP,
    CONF_ROOM_NAME,
    CONF_ROOMS,
    CONF_SLEEP_ENTITY,
    CONF_SUN_ENTITY,
    CONF_SUN_ELEVATION_SENSOR,
    CONF_TEMP_SENSOR,
    CONF_UV_SENSOR,
    CONF_UPDATE_INTERVAL,
    CONF_WEATHER_ENTITY,
    DEFAULT_LEARNING_RATE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


def _global_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Optional(CONF_WEATHER_ENTITY, default=defaults.get(CONF_WEATHER_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_SUN_ENTITY, default=defaults.get(CONF_SUN_ENTITY, "sun.sun")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sun")
            ),
            vol.Optional(CONF_SLEEP_ENTITY, default=defaults.get(CONF_SLEEP_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_datetime")
            ),
            vol.Optional(CONF_SUN_ELEVATION_SENSOR, default=defaults.get(CONF_SUN_ELEVATION_SENSOR)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_UV_SENSOR, default=defaults.get(CONF_UV_SENSOR)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_UPDATE_INTERVAL, default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): vol.All(
                vol.Coerce(int), vol.Range(min=60, max=3600)
            ),
            vol.Optional(CONF_LEARNING_RATE, default=defaults.get(CONF_LEARNING_RATE, DEFAULT_LEARNING_RATE)): vol.All(
                vol.Coerce(float), vol.Range(min=0.001, max=0.2)
            ),
            vol.Optional(CONF_APPLY_CHANGES, default=defaults.get(CONF_APPLY_CHANGES, False)): bool,
        }
    )


def _room_schema(room: dict[str, Any] | None) -> vol.Schema:
    defaults = room or {}
    return vol.Schema(
        {
            vol.Required(CONF_ROOM_NAME, default=defaults.get(CONF_ROOM_NAME, "")): str,
            vol.Optional(CONF_AREA_ID, default=defaults.get(CONF_AREA_ID, "")): selector.AreaSelector(),
            vol.Required(CONF_CLIMATE_ENTITY, default=defaults.get(CONF_CLIMATE_ENTITY, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            vol.Required(CONF_TEMP_SENSOR, default=defaults.get(CONF_TEMP_SENSOR, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
            vol.Optional(CONF_LIGHT_ENTITIES, default=defaults.get(CONF_LIGHT_ENTITIES, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Optional(CONF_EXTRA_SENSORS, default=defaults.get(CONF_EXTRA_SENSORS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Required(CONF_DAY_TEMP, default=defaults.get(CONF_DAY_TEMP, 21.0)): vol.Coerce(float),
            vol.Required(CONF_NIGHT_TEMP, default=defaults.get(CONF_NIGHT_TEMP, 18.0)): vol.Coerce(float),
            vol.Required(CONF_DAY_START, default=defaults.get(CONF_DAY_START, "07:00")): str,
            vol.Required(CONF_NIGHT_START, default=defaults.get(CONF_NIGHT_START, "22:30")): str,
            vol.Optional(CONF_MORNING_TIME, default=defaults.get(CONF_MORNING_TIME, "06:30")): str,
            vol.Optional(CONF_MORNING_TEMP, default=defaults.get(CONF_MORNING_TEMP, 21.0)): vol.Coerce(float),
            vol.Optional(CONF_MIN_TEMP, default=defaults.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)): vol.Coerce(float),
            vol.Optional(CONF_MAX_TEMP, default=defaults.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)): vol.Coerce(float),
        }
    )


class WavinSmartHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wavin Smart Heat."""

    VERSION = 1

    def __init__(self) -> None:
        self._global: dict[str, Any] = {}
        self._rooms: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._global = user_input
            return await self.async_step_room()

        return self.async_show_form(step_id="user", data_schema=_global_schema({}))

    async def async_step_room(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._rooms.append(user_input)
            return await self.async_step_add_another()

        return self.async_show_form(step_id="room", data_schema=_room_schema({}))

    async def async_step_add_another(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            if user_input.get("add_another"):
                return await self.async_step_room()
            return self.async_create_entry(
                title="Wavin Smart Heat",
                data={
                    **self._global,
                    CONF_ROOMS: self._rooms,
                },
            )

        schema = vol.Schema({vol.Required("add_another", default=False): bool})
        return self.async_show_form(step_id="add_another", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return WavinSmartHeatOptionsFlow(config_entry)


class WavinSmartHeatOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Wavin Smart Heat."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = dict(self._entry.options)
        return self.async_show_form(step_id="init", data_schema=_global_schema(defaults))
