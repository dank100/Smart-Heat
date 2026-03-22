"""Coordinator for Wavin Smart Heat."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Any
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_APPLY_CHANGES,
    CONF_AREA_ID,
    CONF_CLIMATE_ENTITY,
    CONF_DAY_START,
    CONF_DAY_TEMP,
    CONF_EXTRA_SENSORS,
    CONF_LEARNING_RATE,
    CONF_LIGHT_ENTITIES,
    CONF_OCCUPANCY_ENTITIES,
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
    CONF_WINDOW_SENSORS,
    DEFAULT_LEARNING_RATE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)


@dataclass
class RoomConfig:
    room_name: str
    area_id: str
    climate_entity: str
    temp_sensor: str
    light_entities: list[str]
    occupancy_entities: list[str]
    window_sensors: list[str]
    extra_sensors: list[str]
    day_temp: float
    night_temp: float
    day_start: str
    night_start: str
    morning_time: str
    morning_temp: float
    min_temp: float
    max_temp: float


class WavinSmartHeatCoordinator:
    """Main coordinator for Wavin Smart Heat."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.model_state: dict[str, Any] = {}
        self.room_states: dict[str, dict[str, Any]] = {}
        self.global_state: dict[str, Any] = {}
        self.global_units: dict[str, str] = {}
        self.data_source_info: dict[str, str | None] = {}
        self._unsub_interval = None
        self.signal_update = f"{DOMAIN}_update_{entry.entry_id}"
        self._logger = logging.getLogger(__name__)

    async def async_initialize(self) -> None:
        stored = await self.store.async_load()
        self.model_state = stored or {}
        await self._async_update()

        interval = self._get_update_interval()
        self._unsub_interval = async_track_time_interval(
            self.hass, self._handle_interval, timedelta(seconds=interval)
        )
        self.hass.async_create_task(self._async_delayed_update())

        if not self.hass.services.has_service(DOMAIN, "apply_recommendations"):
            self.hass.services.async_register(
                DOMAIN,
                "apply_recommendations",
                self._handle_apply_service,
            )

    async def _async_delayed_update(self) -> None:
        await asyncio.sleep(30)
        await self._async_update()

    @callback
    def _handle_interval(self, now: datetime) -> None:
        self.hass.async_create_task(self._async_update())

    def _get_update_interval(self) -> int:
        return int(self.entry.options.get(CONF_UPDATE_INTERVAL, self.entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)))

    def _get_learning_rate(self) -> float:
        return float(self.entry.options.get(CONF_LEARNING_RATE, self.entry.data.get(CONF_LEARNING_RATE, DEFAULT_LEARNING_RATE)))

    def _apply_changes_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_APPLY_CHANGES, self.entry.data.get(CONF_APPLY_CHANGES, False)))

    def _get_weather_entity(self) -> str:
        return str(self.entry.options.get(CONF_WEATHER_ENTITY, self.entry.data.get(CONF_WEATHER_ENTITY, "")))

    def _get_sun_entity(self) -> str:
        return str(self.entry.options.get(CONF_SUN_ENTITY, self.entry.data.get(CONF_SUN_ENTITY, "sun.sun")))

    def _get_sleep_entity(self) -> str:
        return str(self.entry.options.get(CONF_SLEEP_ENTITY, self.entry.data.get(CONF_SLEEP_ENTITY, "")))

    def _get_sun_elevation_sensor(self) -> str:
        return str(self.entry.options.get(CONF_SUN_ELEVATION_SENSOR, self.entry.data.get(CONF_SUN_ELEVATION_SENSOR, "")))

    def _get_uv_sensor(self) -> str:
        return str(self.entry.options.get(CONF_UV_SENSOR, self.entry.data.get(CONF_UV_SENSOR, "")))

    def _room_configs(self) -> list[RoomConfig]:
        rooms = self.entry.data.get(CONF_ROOMS, [])
        configs: list[RoomConfig] = []
        for room in rooms:
            configs.append(
                RoomConfig(
                    room_name=room[CONF_ROOM_NAME],
                    area_id=room.get(CONF_AREA_ID, ""),
                    climate_entity=room[CONF_CLIMATE_ENTITY],
                    temp_sensor=room[CONF_TEMP_SENSOR],
                    light_entities=room.get(CONF_LIGHT_ENTITIES, []),
                    occupancy_entities=room.get(CONF_OCCUPANCY_ENTITIES, []),
                    window_sensors=room.get(CONF_WINDOW_SENSORS, []),
                    extra_sensors=room.get(CONF_EXTRA_SENSORS, []),
                    day_temp=float(room[CONF_DAY_TEMP]),
                    night_temp=float(room[CONF_NIGHT_TEMP]),
                    day_start=room[CONF_DAY_START],
                    night_start=room[CONF_NIGHT_START],
                    morning_time=room.get(CONF_MORNING_TIME, "06:30"),
                    morning_temp=float(room.get(CONF_MORNING_TEMP, room[CONF_DAY_TEMP])),
                    min_temp=float(room.get(CONF_MIN_TEMP, 17.0)),
                    max_temp=float(room.get(CONF_MAX_TEMP, 24.0)),
                )
            )
        return configs

    async def _async_update(self) -> None:
        weather_entity = self._resolve_weather_entity()
        sun_entity = self._get_sun_entity()
        sun_elevation_sensor = self._get_sun_elevation_sensor()
        uv_sensor = self._get_uv_sensor()
        sleep_entity = self._get_sleep_entity()
        sleep_time = self._get_sleep_time(sleep_entity)
        learning_rate = self._get_learning_rate()

        global_values = self._get_global_values(
            weather_entity,
            sun_entity,
            sun_elevation_sensor,
            uv_sensor,
        )
        self.global_state = global_values
        # Units are derived from the weather entity when available.
        self.global_units = self._get_global_units(weather_entity)
        self.data_source_info = self._data_source_info()

        for room in self._room_configs():
            current_temp = self._get_float_state(room.temp_sensor)
            has_real_temp = current_temp is not None
            if current_temp is None:
                current_temp = self._get_climate_current_temp(room.climate_entity)
                has_real_temp = current_temp is not None
            if current_temp is None:
                current_temp = self._get_climate_target_temp(room.climate_entity)
            if current_temp is None:
                current_temp = self._get_last_temp(room.room_name)
            if current_temp is None:
                current_temp = room.night_temp

            occupied = self._is_room_active(room)
            effective_sleep_time = None if occupied else sleep_time

            features = self._build_features(
                room,
                global_values,
                effective_sleep_time,
            )
            if has_real_temp:
                predicted_delta = self._predict_and_learn(room.room_name, features, current_temp, learning_rate)
            else:
                predicted_delta = self._predict_only(room.room_name, features)

            expected_temp = self._expected_temp(room, effective_sleep_time, current_temp)
            recommended_target = self._recommend_target(room, current_temp, expected_temp, predicted_delta)

            self.room_states[room.room_name] = {
                "predicted_delta": predicted_delta,
                "expected_temp": expected_temp,
                "recommended_target": recommended_target,
                "current_temp": current_temp,
                "sleep_time": effective_sleep_time.isoformat() if effective_sleep_time else None,
                "confidence": self._confidence(room.room_name, features),
                "data_source": self.data_source_info,
                "features": features,
            }

            if self._apply_changes_enabled():
                await self._async_apply_target(room, recommended_target)

        await self.store.async_save(self.model_state)
        async_dispatcher_send(self.hass, self.signal_update)

    def _build_features(
        self,
        room: RoomConfig,
        global_values: dict[str, float],
        sleep_time: time | None,
    ) -> dict[str, float]:
        features: dict[str, float] = {}
        features.update(global_values)

        features["window_open"] = 1.0 if self._is_window_open(room) else 0.0

        if sleep_time is not None:
            minutes_until = self._minutes_until_time(sleep_time)
            features["minutes_until_sleep_end"] = minutes_until

        for entity_id in room.extra_sensors:
            value = self._get_float_state(entity_id)
            if value is not None:
                features[f"sensor_{entity_id}"] = value

        features["bias"] = 1.0
        return features

    def _predict_and_learn(
        self,
        room_name: str,
        features: dict[str, float],
        current_temp: float,
        learning_rate: float,
    ) -> float:
        model = self.model_state.setdefault(room_name, {
            "weights": {},
            "last_temp": None,
            "last_features": None,
            "samples": 0,
        })

        weights: dict[str, float] = model.setdefault("weights", {})
        for key in features:
            weights.setdefault(key, 0.0)

        last_temp = model.get("last_temp")
        last_features = model.get("last_features")
        if last_temp is not None and last_features:
            y = current_temp - float(last_temp)
            pred = sum(weights.get(k, 0.0) * float(v) for k, v in last_features.items())
            error = y - pred
            for k, v in last_features.items():
                weights[k] = weights.get(k, 0.0) + learning_rate * error * float(v)
            model["samples"] = int(model.get("samples", 0)) + 1

        model["last_temp"] = current_temp
        model["last_features"] = features

        prediction = sum(weights.get(k, 0.0) * float(v) for k, v in features.items())
        return float(prediction)

    def _predict_only(self, room_name: str, features: dict[str, float]) -> float:
        model = self.model_state.setdefault(room_name, {
            "weights": {},
            "last_temp": None,
            "last_features": None,
            "samples": 0,
        })
        weights: dict[str, float] = model.setdefault("weights", {})
        for key in features:
            weights.setdefault(key, 0.0)
        prediction = sum(weights.get(k, 0.0) * float(v) for k, v in features.items())
        return float(prediction)

    def _expected_temp(self, room: RoomConfig, sleep_time: time | None, current_temp: float) -> float:
        now = dt_util.now()
        day_start = self._parse_time(room.day_start)
        night_start = self._parse_time(room.night_start)

        expected = room.day_temp
        if day_start and night_start:
            if self._is_night(now, day_start, night_start):
                expected = room.night_temp

        morning_time = self._parse_time(room.morning_time)
        if sleep_time is not None:
            morning_time = sleep_time

        if morning_time:
            preheat_minutes = self._compute_preheat_minutes(current_temp, room.morning_temp, self._is_window_open(room))
            preheat_start = (
                datetime.combine(now.date(), morning_time)
                - timedelta(minutes=preheat_minutes)
            ).time()
            if self._is_time_between(now.time(), preheat_start, morning_time):
                expected = max(expected, room.morning_temp)

        return expected

    def _recommend_target(
        self,
        room: RoomConfig,
        current_temp: float,
        expected_temp: float,
        predicted_delta: float,
    ) -> float:
        loss_comp = max(0.0, -predicted_delta) * 2.0
        target = expected_temp + loss_comp
        if current_temp < expected_temp:
            target = max(target, expected_temp + 0.2)

        target = min(max(target, room.min_temp), room.max_temp)
        return round(target, 1)

    def _compute_preheat_minutes(self, current_temp: float, target_temp: float, window_open: bool) -> int:
        # Dynamic preheat based on weather-driven heat loss and temperature gap.
        outside = float(self.global_state.get("outside_temp", 10.0))
        wind = float(self.global_state.get("wind_speed", 0.0))
        clouds = float(self.global_state.get("cloud_coverage", 50.0))
        temp_gap = max(0.0, target_temp - current_temp)

        minutes = 40.0
        minutes += temp_gap * 8.0
        minutes += max(0.0, 18.0 - outside) * 2.0
        minutes += wind * 2.0
        minutes += max(0.0, clouds - 50.0) * 0.2
        if window_open:
            minutes += 20.0

        return int(max(30, min(180, minutes)))

    async def _async_apply_target(self, room: RoomConfig, target: float) -> None:
        state = self.hass.states.get(room.climate_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            self._logger.debug("Climate entity %s unavailable, skipping apply", room.climate_entity)
            return
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": room.climate_entity,
                "temperature": target,
            },
            blocking=False,
        )

    async def _handle_apply_service(self, call) -> None:
        for room in self._room_configs():
            state = self.room_states.get(room.room_name)
            if not state:
                continue
            await self._async_apply_target(room, state["recommended_target"])

    def _lights_on(self, room: RoomConfig) -> bool:
        light_entities = list(room.light_entities)
        if not light_entities and room.area_id:
            light_entities = self._lights_from_area(room.area_id)
        for entity_id in light_entities:
            state = self.hass.states.get(entity_id)
            if state and state.state == "on":
                return True
        return False

    def _is_room_active(self, room: RoomConfig) -> bool:
        if self._lights_on(room):
            return True
        for entity_id in room.occupancy_entities:
            state = self.hass.states.get(entity_id)
            if state and state.state == "on":
                return True
        return False

    def _is_window_open(self, room: RoomConfig) -> bool:
        for entity_id in room.window_sensors:
            state = self.hass.states.get(entity_id)
            if state and state.state == "on":
                return True
        return False

    def _lights_from_area(self, area_id: str) -> list[str]:
        registry = async_get_entity_registry(self.hass)
        entities = registry.entities.values()
        return [entry.entity_id for entry in entities if entry.area_id == area_id and entry.domain == "light"]

    def _get_sleep_time(self, sleep_entity: str) -> time | None:
        if not sleep_entity:
            return None
        state = self.hass.states.get(sleep_entity)
        if not state:
            return None
        return self._parse_time_from_state(state.state)

    def _get_float_state(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    def _get_climate_current_temp(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            value = state.attributes.get("current_temperature")
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _get_climate_target_temp(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            value = state.attributes.get("temperature")
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _get_last_temp(self, room_name: str) -> float | None:
        model = self.model_state.get(room_name)
        if not model:
            return None
        last_temp = model.get("last_temp")
        try:
            return float(last_temp) if last_temp is not None else None
        except (TypeError, ValueError):
            return None

    def _resolve_weather_entity(self) -> str:
        weather_entity = self._get_weather_entity()
        if weather_entity:
            return weather_entity
        candidates = self.hass.states.async_all("weather")
        if candidates:
            return candidates[0].entity_id
        return ""

    def _get_global_values(
        self,
        weather_entity: str,
        sun_entity: str,
        sun_elevation_sensor: str,
        uv_sensor: str,
    ) -> dict[str, float]:
        values: dict[str, float] = {
            "outside_temp": 10.0,
            "wind_speed": 0.0,
            "wind_bearing": 0.0,
            "wind_gust_speed": 0.0,
            "humidity": 0.0,
            "cloud_coverage": 0.0,
            "pressure": 0.0,
            "visibility": 0.0,
            "uv_index": 0.0,
        }

        weather_state = self.hass.states.get(weather_entity) if weather_entity else None
        if weather_state is not None:
            values["outside_temp"] = self._get_attr_float(weather_state.attributes, "temperature")
            values["wind_speed"] = self._get_attr_float(weather_state.attributes, "wind_speed")
            values["wind_bearing"] = self._get_attr_float(weather_state.attributes, "wind_bearing")
            values["wind_gust_speed"] = self._get_attr_float(weather_state.attributes, "wind_gust_speed")
            values["humidity"] = self._get_attr_float(weather_state.attributes, "humidity")
            values["cloud_coverage"] = self._get_attr_float(weather_state.attributes, "cloud_coverage")
            values["pressure"] = self._get_attr_float(weather_state.attributes, "pressure")
            values["visibility"] = self._get_attr_float(weather_state.attributes, "visibility")

        sun_state = self.hass.states.get(sun_entity) if sun_entity else None
        if sun_state is not None:
            values["sun_rising"] = 1.0 if sun_state.state == "above_horizon" else 0.0

        if sun_elevation_sensor:
            value = self._get_float_state(sun_elevation_sensor)
            if value is not None:
                values["sun_elevation"] = value
        elif sun_state is not None:
            values["sun_elevation"] = self._get_attr_float(sun_state.attributes, "elevation")

        if uv_sensor:
            value = self._get_float_state(uv_sensor)
            if value is not None:
                values["uv_index"] = value
        elif weather_state is not None:
            values["uv_index"] = self._get_attr_float(weather_state.attributes, "uv_index")

        values["bias"] = 1.0
        return values

    def _get_global_units(self, weather_entity: str) -> dict[str, str]:
        units: dict[str, str] = {}
        weather_state = self.hass.states.get(weather_entity) if weather_entity else None
        if weather_state is None:
            return units
        attrs = weather_state.attributes
        if (unit := attrs.get("wind_speed_unit")):
            units["wind_speed"] = unit
            units["wind_gust_speed"] = unit
        if (unit := attrs.get("pressure_unit")):
            units["pressure"] = unit
        if (unit := attrs.get("visibility_unit")):
            units["visibility"] = unit
        if (unit := attrs.get("temperature_unit")):
            units["outside_temp"] = unit
        return units

    def _confidence(self, room_name: str, features: dict[str, float]) -> float:
        model = self.model_state.get(room_name, {})
        samples = float(model.get("samples", 0))
        sample_factor = min(1.0, samples / 50.0)
        feature_factor = 1.0 if features else 0.4
        return round(sample_factor * feature_factor, 2)

    def _data_source_info(self) -> dict[str, str | None]:
        return {
            "weather_entity": self._resolve_weather_entity() or None,
            "sun_entity": self._get_sun_entity() or None,
            "sun_elevation_sensor": self._get_sun_elevation_sensor() or None,
            "uv_sensor": self._get_uv_sensor() or None,
        }

    @staticmethod
    def _get_attr_float(attrs: dict[str, Any], key: str) -> float:
        try:
            value = attrs.get(key)
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _parse_time(value: str) -> time | None:
        try:
            parts = value.split(":")
            return time(hour=int(parts[0]), minute=int(parts[1]))
        except (IndexError, ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_time_from_state(value: str) -> time | None:
        if not value:
            return None
        if "T" in value:
            try:
                return dt_util.parse_datetime(value).time()
            except (TypeError, ValueError):
                return None
        return WavinSmartHeatCoordinator._parse_time(value)

    def _minutes_until_time(self, target: time) -> float:
        now = dt_util.now()
        target_dt = datetime.combine(now.date(), target, tzinfo=now.tzinfo)
        if target_dt < now:
            target_dt += timedelta(days=1)
        return (target_dt - now).total_seconds() / 60.0

    @staticmethod
    def _is_night(now: datetime, day_start: time, night_start: time) -> bool:
        return not WavinSmartHeatCoordinator._is_time_between(now.time(), day_start, night_start)

    @staticmethod
    def _is_time_between(now: time, start: time, end: time) -> bool:
        if start <= end:
            return start <= now < end
        return now >= start or now < end
