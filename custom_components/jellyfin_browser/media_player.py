"""Media player entities for controllable Jellyfin sessions."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JellyfinBrowserCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jellyfin remote player entities."""
    coordinator: JellyfinBrowserCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_session_ids: set[str] = set()

    def _async_sync_entities() -> None:
        new_entities = []
        for session in coordinator.data["controllable_sessions"]:
            session_id = session["Id"]
            if session_id in known_session_ids:
                continue
            known_session_ids.add(session_id)
            new_entities.append(JellyfinSessionMediaPlayer(coordinator, entry, session_id))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))
    _async_sync_entities()


class JellyfinSessionMediaPlayer(CoordinatorEntity[JellyfinBrowserCoordinator], MediaPlayerEntity):
    """Represent a remote Jellyfin session as a media player."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, coordinator: JellyfinBrowserCoordinator, entry: ConfigEntry, session_id: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._session_id = session_id
        self._attr_unique_id = f"{entry.entry_id}_{session_id}"

    def _session(self) -> dict[str, Any] | None:
        for session in self.coordinator.data["controllable_sessions"]:
            if session.get("Id") == self._session_id:
                return session
        return None

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._session() is not None

    @property
    def name(self) -> str | None:
        """Return the display name."""
        session = self._session()
        if not session:
            return None
        return session.get("DeviceName") or session.get("Client") or "Jellyfin Device"

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the player state."""
        session = self._session()
        if not session:
            return MediaPlayerState.OFF

        play_state = session.get("PlayState") or {}
        if session.get("NowPlayingItem"):
            return MediaPlayerState.PAUSED if play_state.get("IsPaused") else MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def media_title(self) -> str | None:
        """Return the title currently playing."""
        session = self._session()
        if not session:
            return None
        return (session.get("NowPlayingItem") or {}).get("Name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose session metadata."""
        session = self._session() or {}
        return {
            "session_id": self._session_id,
            "client": session.get("Client"),
            "user": session.get("UserName"),
            "device_name": session.get("DeviceName"),
            "application_version": session.get("ApplicationVersion"),
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for this session."""
        session = self._session() or {}
        return {
            "identifiers": {(DOMAIN, f"{self._entry.entry_id}_{self._session_id}")},
            "name": self.name,
            "manufacturer": "Jellyfin",
            "model": session.get("Client") or "Remote Session",
            "sw_version": session.get("ApplicationVersion"),
            "via_device": (DOMAIN, self._entry.entry_id),
        }

    async def async_media_pause(self) -> None:
        """Pause remote playback."""
        await self.coordinator.client.async_send_playstate(self._session_id, "Pause")

    async def async_media_play(self) -> None:
        """Resume remote playback."""
        await self.coordinator.client.async_send_playstate(self._session_id, "Unpause")

    async def async_media_stop(self) -> None:
        """Stop remote playback."""
        await self.coordinator.client.async_send_playstate(self._session_id, "Stop")

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Play a Jellyfin item on the remote session."""
        del media_type
        enqueue = kwargs.get("enqueue")
        play_command = "PlayNext" if enqueue else "PlayNow"
        await self.coordinator.client.async_play_media(self._session_id, media_id, play_command=play_command)
        await self.coordinator.async_request_refresh()
