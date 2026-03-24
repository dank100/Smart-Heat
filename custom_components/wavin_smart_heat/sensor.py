"""Sensor platform for Wavin Smart Heat."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOMS, CONF_ROOM_NAME, DOMAIN
from .coordinator import WavinSmartHeatCoordinator


@dataclass
class WavinSensorDescription(SensorEntityDescription):
    key: str
    unit: str | None = None


SENSOR_TYPES: list[WavinSensorDescription] = [
    WavinSensorDescription(key="current_temp", name="Current Temp", unit="°C"),
    WavinSensorDescription(key="recommended_target", name="Recommended Target Temp", unit="°C"),
    WavinSensorDescription(key="confidence", name="Prediction Confidence", unit=None),
]

GLOBAL_SENSOR_TYPES: list[WavinSensorDescription] = [
    WavinSensorDescription(key="sun_elevation", name="Sun Elevation", unit="°"),
    WavinSensorDescription(key="wind_speed", name="Wind Speed", unit=None),
    WavinSensorDescription(key="wind_bearing", name="Wind Bearing", unit="°"),
    WavinSensorDescription(key="wind_gust_speed", name="Wind Gust Speed", unit=None),
    WavinSensorDescription(key="outside_temp", name="Outside Temperature", unit=None),
    WavinSensorDescription(key="humidity", name="Humidity", unit="%"),
    WavinSensorDescription(key="cloud_coverage", name="Cloud Coverage", unit="%"),
    WavinSensorDescription(key="pressure", name="Pressure", unit=None),
    WavinSensorDescription(key="visibility", name="Visibility", unit=None),
    WavinSensorDescription(key="uv_index", name="UV Index", unit=None),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WavinSmartHeatCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for room in entry.data.get(CONF_ROOMS, []):
        room_name = room.get(CONF_ROOM_NAME)
        if not room_name:
            continue
        for description in SENSOR_TYPES:
            entities.append(WavinSmartHeatSensor(coordinator, room_name, description))

    has_weather = bool(coordinator._resolve_weather_entity())
    has_sun_elevation = bool(coordinator._get_sun_elevation_sensor()) or bool(coordinator._get_sun_entity())
    has_uv = bool(coordinator._get_uv_sensor()) or has_weather

    for description in GLOBAL_SENSOR_TYPES:
        if description.key == "sun_elevation" and not has_sun_elevation:
            continue
        if description.key == "uv_index" and not has_uv:
            continue
        entities.append(WavinSmartHeatGlobalSensor(coordinator, description))

    async_add_entities(entities)


class WavinSmartHeatSensor(SensorEntity):
    """Sensor entity for Wavin Smart Heat."""

    def __init__(
        self,
        coordinator: WavinSmartHeatCoordinator,
        room_name: str,
        description: WavinSensorDescription,
    ) -> None:
        self.coordinator = coordinator
        self.room_name = room_name
        self.entity_description = description
        self._attr_name = f"{room_name} {description.name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room_name}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Wavin Smart Heat",
        )
        self._unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, self.coordinator.signal_update, self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    def _handle_update(self) -> None:
        self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    @property
    def available(self) -> bool:
        return self.room_name in self.coordinator.room_states

    @property
    def native_value(self) -> Any:
        state = self.coordinator.room_states.get(self.room_name)
        if not state:
            return None
        value = state.get(self.entity_description.key)
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        if abs(value) > 100.0:
            return None
        if self.entity_description.key == "predicted_delta":
            return round(value, 2)
        return round(value, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self.coordinator.room_states.get(self.room_name, {})
        if self.entity_description.key != "recommended_target":
            return {}
        return {
            "current_temp": state.get("current_temp"),
            "current_temp_source": state.get("current_temp_source"),
            "sleep_time": state.get("sleep_time"),
            "data_source": state.get("data_source"),
            "recommendation_components": state.get("recommendation_components"),
        }


class WavinSmartHeatGlobalSensor(SensorEntity):
    """Global sensor entity for Wavin Smart Heat."""

    def __init__(
        self,
        coordinator: WavinSmartHeatCoordinator,
        description: WavinSensorDescription,
    ) -> None:
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_name = f"Wavin {description.name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_global_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Wavin Smart Heat",
        )
        self._unsub_dispatcher = None

    async def async_added_to_hass(self) -> None:
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, self.coordinator.signal_update, self._handle_update
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    def _handle_update(self) -> None:
        self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    @property
    def available(self) -> bool:
        return self.entity_description.key in self.coordinator.global_state

    @property
    def native_value(self) -> Any:
        value = self.coordinator.global_state.get(self.entity_description.key)
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        return round(value, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "data_source": self.coordinator.data_source_info,
        }

    @property
    def native_unit_of_measurement(self) -> str | None:
        unit = self.coordinator.global_units.get(self.entity_description.key)
        if unit:
            return unit
        return self.entity_description.unit
