"""Wavin Smart Heat integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

    await _async_ensure_wavin_dashboard(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_ensure_wavin_dashboard(hass: HomeAssistant) -> None:
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
                            "entities": [],
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


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
