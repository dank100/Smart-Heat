"""Sensors for Jellyfin Browser."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MAX_ATTRIBUTE_ITEMS
from .coordinator import JellyfinBrowserCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jellyfin Browser sensors."""
    coordinator: JellyfinBrowserCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JellyfinLibrarySensor(coordinator, entry),
            JellyfinDevicesSensor(coordinator, entry),
            JellyfinLiveTvSensor(coordinator, entry),
        ]
    )


class JellyfinBaseSensor(CoordinatorEntity[JellyfinBrowserCoordinator], SensorEntity):
    """Base sensor implementation."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JellyfinBrowserCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> dict[str, Any]:
        """Return the integration device."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self.coordinator.data["server_name"],
            "manufacturer": "Jellyfin",
            "model": "Server",
            "sw_version": self.coordinator.data.get("version"),
        }


class JellyfinLibrarySensor(JellyfinBaseSensor):
    """Expose a summary of the Jellyfin library."""

    _attr_name = "Library"
    _attr_icon = "mdi:movie-open-outline"

    def __init__(self, coordinator: JellyfinBrowserCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_library"

    @property
    def native_value(self) -> int:
        """Return the number of indexed items."""
        return self.coordinator.data["item_count"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose a small sample of library items."""
        items = self.coordinator.data["items"][:MAX_ATTRIBUTE_ITEMS]
        return {
            "server": self.coordinator.data["server_name"],
            "indexed_item_limit": len(self.coordinator.data["items"]),
            "item_type_counts": self.coordinator.data["item_type_counts"],
            "sample_items": [
                {
                    "id": item.get("Id"),
                    "name": item.get("Name"),
                    "type": item.get("Type"),
                    "year": item.get("ProductionYear"),
                }
                for item in items
            ],
        }


class JellyfinDevicesSensor(JellyfinBaseSensor):
    """Expose a summary of castable Jellyfin devices."""

    _attr_name = "Cast Devices"
    _attr_icon = "mdi:cast-connected"

    def __init__(self, coordinator: JellyfinBrowserCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_devices"

    @property
    def native_value(self) -> int:
        """Return the number of controllable devices."""
        return len(self.coordinator.data["controllable_sessions"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a sample of active cast devices."""
        return {
            "devices": [
                {
                    "session_id": session.get("Id"),
                    "name": session.get("DeviceName") or session.get("Client"),
                    "client": session.get("Client"),
                    "user": session.get("UserName"),
                    "app": session.get("ApplicationVersion"),
                    "now_playing": (session.get("NowPlayingItem") or {}).get("Name"),
                }
                for session in self.coordinator.data["controllable_sessions"][:MAX_ATTRIBUTE_ITEMS]
            ]
        }


class JellyfinLiveTvSensor(JellyfinBaseSensor):
    """Expose a summary of Jellyfin live TV channels."""

    _attr_name = "Live TV"
    _attr_icon = "mdi:television-guide"

    def __init__(self, coordinator: JellyfinBrowserCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_live_tv"

    @property
    def native_value(self) -> int:
        """Return the number of available live TV channels."""
        return self.coordinator.data["live_tv_channel_count"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a sample of live TV channels and programs."""
        channels = self.coordinator.data["live_tv_channels"][:MAX_ATTRIBUTE_ITEMS]
        programs = self.coordinator.data["live_tv_programs"][:MAX_ATTRIBUTE_ITEMS]
        return {
            "guide_days": self.coordinator.data.get("guide_info", {}).get("DaysInAdvance"),
            "channels": [
                {
                    "id": channel.get("Id"),
                    "name": channel.get("Name"),
                    "number": channel.get("ChannelNumber"),
                    "type": channel.get("Type"),
                    "current_program": (channel.get("CurrentProgram") or {}).get("Name"),
                }
                for channel in channels
            ],
            "upcoming_programs": [
                {
                    "id": program.get("Id"),
                    "name": program.get("Name"),
                    "channel_id": program.get("ChannelId"),
                    "start_date": program.get("StartDate"),
                    "end_date": program.get("EndDate"),
                }
                for program in programs
            ],
        }
