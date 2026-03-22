"""Wavin Smart Heat integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.storage import Store

from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.components.lovelace.const import (
    CONF_ICON,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TITLE,
    CONF_URL_PATH,
)

from .const import DOMAIN, PLATFORMS
from .coordinator import WavinSmartHeatCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Wavin Smart Heat from a config entry."""
    coordinator = WavinSmartHeatCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def _setup_dashboard(_event) -> None:
        await _async_ensure_wavin_dashboard(hass, entry.entry_id)

    if hass.is_running:
        hass.async_create_task(_async_ensure_wavin_dashboard(hass, entry.entry_id))
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _setup_dashboard)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_ensure_wavin_dashboard(hass: HomeAssistant, entry_id: str) -> None:
    """Ensure a Wavin Heat Lovelace dashboard exists with a basic view."""
    dashboards = lovelace_dashboard.DashboardsCollection(hass)
    await dashboards.async_load()

    url_path = "wavin-heat"
    existing = None
    for item in dashboards.async_items():
        if item[CONF_URL_PATH] == url_path:
            existing = item
            break

    if existing is None:
        await dashboards.async_create_item(
            {
                CONF_TITLE: "Wavin Heat",
                CONF_ICON: "mdi:fire",
                CONF_URL_PATH: url_path,
                CONF_SHOW_IN_SIDEBAR: True,
            }
        )

    # Create a simple default view if none exists.
    store = Store(hass, 1, f"lovelace.{url_path}")
    data = await store.async_load() or {"config": None}
    if data.get("config") is None:
        entity_ids = _collect_room_entity_ids(hass, entry_id)
        data["config"] = {
            "title": "Wavin Heat",
            "views": [
                {
                    "title": "Wavin Heat",
                    "path": "wavin-heat",
                    "cards": [
                        {
                            "type": "entities",
                            "title": "Wavin Smart Heat",
                            "entities": entity_ids,
                        },
                        {
                            "type": "button",
                            "name": "Apply Recommendations",
                            "tap_action": {
                                "action": "call-service",
                                "service": "wavin_smart_heat.apply_recommendations",
                            },
                        },
                    ],
                }
            ],
        }
        await store.async_save(data)


def _collect_room_entity_ids(hass: HomeAssistant, entry_id: str) -> list[str]:
    registry = async_get_entity_registry(hass)
    entities: list[str] = []
    # Room sensors
    room_names = []
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator:
        room_names = [room.room_name for room in coordinator._room_configs()]

    room_keys = [
        "predicted_delta",
        "expected_temp",
        "recommended_target",
        "confidence",
    ]
    for room_name in room_names:
        for key in room_keys:
            unique_id = f"{entry_id}_{room_name}_{key}"
            entry = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entry:
                entities.append(entry)

    # Global sensors (if present)
    global_keys = [
        "sun_elevation",
        "wind_speed",
        "wind_bearing",
        "wind_gust_speed",
        "outside_temp",
        "humidity",
        "cloud_coverage",
        "pressure",
        "visibility",
        "uv_index",
    ]
    for key in global_keys:
        unique_id = f"{entry_id}_global_{key}"
        entry = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entry:
            entities.append(entry)

    return entities


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
