"""Number platform for Wavin Smart Heat."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOMS, CONF_ROOM_NAME, CONF_MIN_TEMP, CONF_MAX_TEMP, DOMAIN
from .coordinator import WavinSmartHeatCoordinator


@dataclass
class WavinNumberDescription(NumberEntityDescription):
    key: str


NUMBER_TYPES: list[WavinNumberDescription] = [
    WavinNumberDescription(
        key="target_override",
        name="Target Temp",
        icon="mdi:thermometer",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WavinSmartHeatCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []

    for room in entry.data.get(CONF_ROOMS, []):
        room_name = room.get(CONF_ROOM_NAME)
        if not room_name:
            continue
        for description in NUMBER_TYPES:
            entities.append(WavinSmartHeatRoomNumber(coordinator, room, description))

    async_add_entities(entities)


class WavinSmartHeatRoomNumber(NumberEntity):
    """Number entity for room target temperature."""

    def __init__(
        self,
        coordinator: WavinSmartHeatCoordinator,
        room: dict,
        description: WavinNumberDescription,
    ) -> None:
        self.coordinator = coordinator
        self.room_name = room[CONF_ROOM_NAME]
        self.entity_description = description
        self._attr_name = f"{self.room_name} {description.name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{self.room_name}_{description.key}"
        self._attr_native_min_value = float(room.get(CONF_MIN_TEMP, 17.0))
        self._attr_native_max_value = float(room.get(CONF_MAX_TEMP, 24.0))
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = "°C"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Wavin Smart Heat",
        )

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        room_config = next((room for room in self.coordinator._room_configs() if room.room_name == self.room_name), None)
        if room_config is None:
            return float(self._attr_native_min_value or 17.0)
        return float(self.coordinator._get_room_target(room_config))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_room_target(self.room_name, value)
