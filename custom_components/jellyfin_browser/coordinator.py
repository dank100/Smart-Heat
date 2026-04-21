"""Coordinator for Jellyfin Browser."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JellyfinApiError, JellyfinClient
from .const import (
    CONF_API_KEY,
    CONF_SERVER_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_LIMIT,
    DOMAIN,
)


class JellyfinBrowserCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage Jellyfin data refreshes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.client = JellyfinClient(
            entry.data[CONF_SERVER_URL],
            entry.data[CONF_API_KEY],
            async_get_clientsession(hass),
        )
        interval_seconds = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL))
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval_seconds),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Jellyfin."""
        try:
            info = await self.client.async_get_public_info()
            items = await self.client.async_get_all_items(limit=DEFAULT_SCAN_LIMIT)
            sessions = await self.client.async_get_sessions()
            now = datetime.now(timezone.utc)
            live_tv_channels = await self.client.async_get_live_tv_channels(limit=DEFAULT_SCAN_LIMIT)
            live_tv_programs = await self.client.async_get_live_tv_programs(
                start=now,
                end=now + timedelta(hours=4),
                limit=DEFAULT_SCAN_LIMIT,
            )
            guide_info = await self.client.async_get_guide_info()
        except JellyfinApiError as err:
            raise UpdateFailed(str(err)) from err

        type_counts = Counter(item.get("Type", "Unknown") for item in items)
        controllable_sessions = [
            session
            for session in sessions
            if session.get("SupportsRemoteControl") and session.get("Id")
        ]

        return {
            "server_name": info.get("ServerName") or self.entry.title or DEFAULT_NAME,
            "version": info.get("Version"),
            "items": items,
            "item_count": len(items),
            "item_type_counts": dict(type_counts),
            "sessions": sessions,
            "controllable_sessions": controllable_sessions,
            "live_tv_channels": live_tv_channels,
            "live_tv_channel_count": len(live_tv_channels),
            "live_tv_programs": live_tv_programs,
            "live_tv_program_count": len(live_tv_programs),
            "guide_info": guide_info,
        }

    async def async_get_content(
        self,
        *,
        search: str | None = None,
        item_types: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch content on demand."""
        return await self.client.async_get_all_items(search=search, item_types=item_types, limit=limit)

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch devices on demand."""
        sessions = await self.client.async_get_sessions()
        return [
            session
            for session in sessions
            if session.get("SupportsRemoteControl") and session.get("Id")
        ]

    async def async_get_live_tv_channels(
        self,
        *,
        channel_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch live TV channels on demand."""
        return await self.client.async_get_live_tv_channels(channel_type=channel_type, limit=limit)

    async def async_get_live_tv_programs(
        self,
        *,
        channel_ids: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch live TV programs on demand."""
        return await self.client.async_get_live_tv_programs(
            channel_ids=channel_ids,
            start=start,
            end=end,
            limit=limit,
        )
