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
    CONF_DAY_TEMP,
    CONF_EXTRA_SENSORS,
    CONF_LEARNING_RATE,
    CONF_LIGHT_ENTITIES,
    CONF_OCCUPANCY_ENTITIES,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_MORNING_TEMP,
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
    CONF_WINDOW_SENSORS,
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
            vol.Optional(CONF_WEATHER_ENTITY, default=defaults.get(CONF_WEATHER_ENTITY)): vol.Any(
                None,
                selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
            ),
            vol.Optional(CONF_SUN_ENTITY, default=defaults.get(CONF_SUN_ENTITY, "sun.sun")): vol.Any(
                None,
                selector.EntitySelector(selector.EntitySelectorConfig(domain="sun")),
            ),
            vol.Optional(CONF_SLEEP_ENTITY, default=defaults.get(CONF_SLEEP_ENTITY)): vol.Any(
                None,
                selector.EntitySelector(selector.EntitySelectorConfig(domain="input_datetime")),
            ),
            vol.Optional(CONF_SUN_ELEVATION_SENSOR, default=defaults.get(CONF_SUN_ELEVATION_SENSOR)): vol.Any(
                None,
                selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            ),
            vol.Optional(CONF_UV_SENSOR, default=defaults.get(CONF_UV_SENSOR)): vol.Any(
                None,
                selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
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
            vol.Optional(CONF_OCCUPANCY_ENTITIES, default=defaults.get(CONF_OCCUPANCY_ENTITIES, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"], multiple=True)
            ),
            vol.Optional(CONF_WINDOW_SENSORS, default=defaults.get(CONF_WINDOW_SENSORS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Optional(CONF_EXTRA_SENSORS, default=defaults.get(CONF_EXTRA_SENSORS, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Required(CONF_DAY_TEMP, default=defaults.get(CONF_DAY_TEMP, 21.0)): vol.Coerce(float),
            vol.Required(CONF_NIGHT_TEMP, default=defaults.get(CONF_NIGHT_TEMP, 18.0)): vol.Coerce(float),
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
        self._options: dict[str, Any] = dict(config_entry.options)
        self._rooms: list[dict[str, Any]] = list(
            config_entry.options.get(CONF_ROOMS, config_entry.data.get(CONF_ROOMS, []))
        )
        self._edit_room_name: str | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            choice = user_input["menu"]
            if choice == "global":
                return await self.async_step_global()
            if choice == "add_room":
                return await self.async_step_add_room()
            if choice == "edit_room":
                return await self.async_step_edit_room_select()
            if choice == "remove_room":
                return await self.async_step_remove_room()
            return await self.async_step_finish()

        schema = vol.Schema(
            {
                vol.Required("menu", default="global"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "global", "label": "Edit global settings"},
                            {"value": "add_room", "label": "Add a room"},
                            {"value": "edit_room", "label": "Edit a room"},
                            {"value": "remove_room", "label": "Remove a room"},
                            {"value": "finish", "label": "Finish"},
                        ],
                        mode="list",
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_global(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_init()

        defaults = {**self._entry.data, **self._options}
        return self.async_show_form(step_id="global", data_schema=_global_schema(defaults))

    async def async_step_add_room(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._rooms.append(user_input)
            return await self.async_step_init()

        return self.async_show_form(step_id="add_room", data_schema=_room_schema({}))

    async def async_step_edit_room_select(self, user_input: dict[str, Any] | None = None):
        room_names = [room.get(CONF_ROOM_NAME, "") for room in self._rooms]
        if user_input is not None:
            self._edit_room_name = user_input[CONF_ROOM_NAME]
            return await self.async_step_edit_room()

        if not room_names:
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required(CONF_ROOM_NAME): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=room_names, mode="list")
                )
            }
        )
        return self.async_show_form(step_id="edit_room_select", data_schema=schema)

    async def async_step_edit_room(self, user_input: dict[str, Any] | None = None):
        if user_input is not None and self._edit_room_name is not None:
            for idx, room in enumerate(self._rooms):
                if room.get(CONF_ROOM_NAME) == self._edit_room_name:
                    self._rooms[idx] = user_input
                    break
            self._edit_room_name = None
            return await self.async_step_init()

        current = {}
        if self._edit_room_name:
            for room in self._rooms:
                if room.get(CONF_ROOM_NAME) == self._edit_room_name:
                    current = room
                    break
        return self.async_show_form(step_id="edit_room", data_schema=_room_schema(current))

    async def async_step_remove_room(self, user_input: dict[str, Any] | None = None):
        room_names = [room.get(CONF_ROOM_NAME, "") for room in self._rooms]
        if user_input is not None:
            name = user_input[CONF_ROOM_NAME]
            self._rooms = [room for room in self._rooms if room.get(CONF_ROOM_NAME) != name]
            return await self.async_step_init()

        if not room_names:
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required(CONF_ROOM_NAME): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=room_names, mode="list")
                )
            }
        )
        return self.async_show_form(step_id="remove_room", data_schema=schema)

    async def async_step_finish(self, user_input: dict[str, Any] | None = None):
        data = {**self._options, CONF_ROOMS: self._rooms}
        return self.async_create_entry(title="", data=data)
