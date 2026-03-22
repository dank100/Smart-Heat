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
    EVENT_LOVELACE_UPDATED,
    LOVELACE_DATA,
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
        existing = await dashboards.async_create_item(
            {
                CONF_TITLE: "Wavin Heat",
                CONF_ICON: "mdi:fire",
                CONF_URL_PATH: url_path,
                CONF_SHOW_IN_SIDEBAR: True,
            }
        )

    # Create or refresh a simple default view.
    dashboard_id = existing["id"]
    store = Store(hass, 1, f"lovelace.{dashboard_id}")
    data = await store.async_load() or {"config": None}
    room_entities, global_entities = _collect_room_entities(hass, entry_id)
    if _needs_dashboard_refresh(data.get("config"), room_entities, global_entities):
        config = _build_default_dashboard_config(room_entities, global_entities)

        lovelace_data = hass.data.get(LOVELACE_DATA)
        dashboard = lovelace_data.dashboards.get(url_path) if lovelace_data else None
        if dashboard is not None:
            await dashboard.async_save(config)
        else:
            data["config"] = config
            await store.async_save(data)
            hass.bus.async_fire(EVENT_LOVELACE_UPDATED, {"url_path": url_path})


def _collect_room_entities(hass: HomeAssistant, entry_id: str) -> tuple[dict[str, list[str]], list[str]]:
    registry = async_get_entity_registry(hass)
    room_entities: dict[str, list[str]] = {}
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
        room_entities[room_name] = []
        for key in room_keys:
            unique_id = f"{entry_id}_{room_name}_{key}"
            entry = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entry:
                room_entities[room_name].append(entry)

    # Global sensors (if present)
    global_entities: list[str] = []
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
            global_entities.append(entry)

    return room_entities, global_entities


def _build_default_dashboard_config(
    room_entities: dict[str, list[str]],
    global_entities: list[str],
) -> dict:
    sections: list[dict] = []
    for room_name, entities in room_entities.items():
        if not entities:
            continue
        sections.append(
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "markdown",
                        "content": f"## {room_name}",
                    },
                    {
                        "type": "entities",
                        "title": f"{room_name} Sensors",
                        "entities": entities,
                    },
                ],
            }
        )

    if global_entities:
        sections.append(
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "markdown",
                        "content": "## Global Sensors",
                    },
                    {
                        "type": "entities",
                        "title": "Global",
                        "entities": global_entities,
                    },
                ],
            }
        )

    return {
        "title": "Wavin Heat",
        "views": [
            {
                "title": "Wavin Heat",
                "path": "wavin-heat",
                "type": "sections",
                "sections": sections
            }
        ],
    }


def _needs_dashboard_refresh(
    config: dict | None,
    room_entities: dict[str, list[str]],
    global_entities: list[str],
) -> bool:
    if config is None:
        return True
    views = config.get("views")
    if not isinstance(views, list) or not views:
        return True
    first_view = views[0]
    sections = first_view.get("sections")
    if not isinstance(sections, list) or not sections:
        return True
    has_any = any(room_entities.values()) or bool(global_entities)
    return has_any and not sections


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
