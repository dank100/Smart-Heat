"""Wavin Smart Heat integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components import frontend

from .const import DOMAIN, PLATFORMS
from .coordinator import WavinSmartHeatCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Wavin Smart Heat from a config entry."""
    coordinator = WavinSmartHeatCoordinator(hass, entry)
    await coordinator.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        sidebar_title="Wavin Heat",
        sidebar_icon="mdi:fire",
        frontend_url_path="wavin_heat",
        config={"mode": "storage"},
        require_admin=False,
        update=True,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        frontend.async_remove_panel(hass, "wavin_heat")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
