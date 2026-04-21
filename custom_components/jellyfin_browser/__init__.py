"""Jellyfin Browser integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    ATTR_CHANNEL_ID,
    ATTR_CHANNEL_IDS,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_END,
    ATTR_ITEM_ID,
    ATTR_ITEM_TYPES,
    ATTR_LIMIT,
    ATTR_SEARCH,
    ATTR_SESSION_ID,
    ATTR_START,
    DOMAIN,
    PLATFORMS,
    SERVICE_GET_CONTENT,
    SERVICE_GET_DEVICES,
    SERVICE_GET_LIVE_TV_CHANNELS,
    SERVICE_GET_LIVE_TV_PROGRAMS,
    SERVICE_PLAY_ON_DEVICE,
    SERVICE_REFRESH,
)
from .coordinator import JellyfinBrowserCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jellyfin Browser from a config entry."""
    coordinator = JellyfinBrowserCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register services for the integration."""
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        return

    async def async_handle_refresh(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        await coordinator.async_request_refresh()

    async def async_handle_get_content(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        items = await coordinator.async_get_content(
            search=call.data.get(ATTR_SEARCH),
            item_types=call.data.get(ATTR_ITEM_TYPES),
            limit=call.data.get(ATTR_LIMIT),
        )
        return {
            "server": coordinator.data["server_name"],
            "count": len(items),
            "items": [_serialize_item(item) for item in items],
        }

    async def async_handle_get_devices(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        devices = await coordinator.async_get_devices()
        return {
            "server": coordinator.data["server_name"],
            "count": len(devices),
            "devices": [_serialize_session(session) for session in devices],
        }

    async def async_handle_get_live_tv_channels(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        channels = await coordinator.async_get_live_tv_channels(
            channel_type=call.data.get("type"),
            limit=call.data.get(ATTR_LIMIT),
        )
        return {
            "server": coordinator.data["server_name"],
            "count": len(channels),
            "channels": [_serialize_channel(channel) for channel in channels],
        }

    async def async_handle_get_live_tv_programs(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        start = datetime.fromisoformat(call.data[ATTR_START]) if call.data.get(ATTR_START) else None
        end = datetime.fromisoformat(call.data[ATTR_END]) if call.data.get(ATTR_END) else None
        channel_ids = call.data.get(ATTR_CHANNEL_IDS)
        if call.data.get(ATTR_CHANNEL_ID):
            channel_ids = [call.data[ATTR_CHANNEL_ID]]
        programs = await coordinator.async_get_live_tv_programs(
            channel_ids=channel_ids,
            start=start,
            end=end,
            limit=call.data.get(ATTR_LIMIT),
        )
        return {
            "server": coordinator.data["server_name"],
            "count": len(programs),
            "programs": [_serialize_program(program) for program in programs],
        }

    async def async_handle_play_on_device(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        session_id = call.data.get(ATTR_SESSION_ID) or _resolve_session_id_from_entity(hass, call)
        if not session_id:
            raise HomeAssistantError("Provide a session_id or target a jellyfin_browser media_player entity.")

        await coordinator.client.async_play_media(session_id, call.data[ATTR_ITEM_ID])
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        async_handle_refresh,
        schema=vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_CONTENT,
        async_handle_get_content,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Optional(ATTR_SEARCH): cv.string,
                vol.Optional(ATTR_ITEM_TYPES): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(ATTR_LIMIT): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DEVICES,
        async_handle_get_devices,
        schema=vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LIVE_TV_CHANNELS,
        async_handle_get_live_tv_channels,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Optional("type"): vol.In(["TV", "Radio"]),
                vol.Optional(ATTR_LIMIT): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LIVE_TV_PROGRAMS,
        async_handle_get_live_tv_programs,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Optional(ATTR_CHANNEL_ID): cv.string,
                vol.Optional(ATTR_CHANNEL_IDS): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(ATTR_START): cv.string,
                vol.Optional(ATTR_END): cv.string,
                vol.Optional(ATTR_LIMIT): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_ON_DEVICE,
        async_handle_play_on_device,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Optional(ATTR_SESSION_ID): cv.string,
                vol.Required(ATTR_ITEM_ID): cv.string,
            }
        ),
    )


def _get_coordinator(hass: HomeAssistant, config_entry_id: str | None) -> JellyfinBrowserCoordinator:
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("No Jellyfin Browser entries are configured.")

    if config_entry_id:
        coordinator = entries.get(config_entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Unknown Jellyfin Browser config_entry_id: {config_entry_id}")
        return coordinator

    if len(entries) == 1:
        return next(iter(entries.values()))

    raise HomeAssistantError("Multiple Jellyfin Browser entries found, provide config_entry_id.")


def _resolve_session_id_from_entity(hass: HomeAssistant, call: ServiceCall) -> str | None:
    entity_ids = call.data.get("entity_id")
    if not entity_ids:
        return None
    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]

    registry = async_get_entity_registry(hass)
    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        if not entry or entry.platform != DOMAIN:
            continue
        unique_id = entry.unique_id
        if "_" not in unique_id:
            continue
        return unique_id.rsplit("_", 1)[-1]
    return None


def _serialize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("Id"),
        "name": item.get("Name"),
        "type": item.get("Type"),
        "year": item.get("ProductionYear"),
        "overview": item.get("Overview"),
        "premiere_date": item.get("PremiereDate"),
        "path": item.get("Path"),
    }


def _serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session.get("Id"),
        "name": session.get("DeviceName") or session.get("Client"),
        "client": session.get("Client"),
        "device_name": session.get("DeviceName"),
        "user": session.get("UserName"),
        "version": session.get("ApplicationVersion"),
        "supports_remote_control": session.get("SupportsRemoteControl"),
        "now_playing": ((session.get("NowPlayingItem") or {}).get("Name")),
    }


def _serialize_channel(channel: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": channel.get("Id"),
        "name": channel.get("Name"),
        "number": channel.get("ChannelNumber"),
        "type": channel.get("Type"),
        "overview": channel.get("Overview"),
        "current_program": ((channel.get("CurrentProgram") or {}).get("Name")),
    }


def _serialize_program(program: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": program.get("Id"),
        "channel_id": program.get("ChannelId"),
        "name": program.get("Name"),
        "overview": program.get("Overview"),
        "start_date": program.get("StartDate"),
        "end_date": program.get("EndDate"),
        "is_live": program.get("IsLive"),
        "is_news": program.get("IsNews"),
        "is_movie": program.get("IsMovie"),
        "is_series": program.get("IsSeries"),
        "is_sports": program.get("IsSports"),
    }
