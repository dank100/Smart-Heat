"""Jellyfin API client."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import MEDIA_TYPES, SCAN_PAGE_SIZE


class JellyfinApiError(Exception):
    """Raised when communication with Jellyfin fails."""


class JellyfinClient:
    """Tiny async Jellyfin client used by the integration."""

    def __init__(self, server_url: str, api_key: str, session: ClientSession) -> None:
        self._server_url = server_url.rstrip("/") + "/"
        self._api_key = api_key
        self._session = session

    @property
    def headers(self) -> dict[str, str]:
        """Return auth headers for Jellyfin."""
        return {
            "Accept": "application/json",
            "Authorization": (
                'MediaBrowser Client="Home Assistant", Device="Home Assistant", '
                'DeviceId="home-assistant", Version="1.0.0", '
                f'Token="{self._api_key}"'
            ),
            "X-Emby-Token": self._api_key,
        }

    async def async_get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        expected_status: Iterable[int] = (200,),
    ) -> Any:
        """Perform a GET request and return JSON."""
        return await self._async_request("get", path, params=params, expected_status=expected_status)

    async def async_post(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        expected_status: Iterable[int] = (200, 204),
    ) -> None:
        """Perform a POST request."""
        await self._async_request(
            "post",
            path,
            params=params,
            json_body=json_body,
            expected_status=expected_status,
        )

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        expected_status: Iterable[int] = (200,),
    ) -> Any:
        """Execute an HTTP request against Jellyfin."""
        url = urljoin(self._server_url, path.lstrip("/"))

        try:
            async with self._session.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json_body,
            ) as response:
                if response.status not in expected_status:
                    text = await response.text()
                    raise JellyfinApiError(f"Unexpected status {response.status}: {text[:200]}")

                if response.content_type == "application/json":
                    return await response.json()

                if response.content_length == 0 or response.status == 204:
                    return None

                return await response.text()
        except (ClientError, ClientResponseError) as err:
            raise JellyfinApiError(str(err)) from err

    async def async_get_public_info(self) -> dict[str, Any]:
        """Fetch public server information."""
        return await self.async_get_json("/System/Info/Public")

    async def async_get_all_items(
        self,
        *,
        search: str | None = None,
        item_types: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch library items, following pagination."""
        all_items: list[dict[str, Any]] = []
        start_index = 0
        requested_types = item_types or MEDIA_TYPES

        while True:
            page_limit = SCAN_PAGE_SIZE
            if limit is not None:
                remaining = limit - len(all_items)
                if remaining <= 0:
                    break
                page_limit = min(page_limit, remaining)

            payload = await self.async_get_json(
                "/Items",
                params={
                    "Recursive": "true",
                    "IncludeItemTypes": ",".join(requested_types),
                    "Fields": "Overview,Path,PremiereDate,ProviderIds",
                    "SortBy": "SortName",
                    "SortOrder": "Ascending",
                    "EnableImages": "false",
                    "EnableTotalRecordCount": "true",
                    "StartIndex": start_index,
                    "Limit": page_limit,
                    **({"SearchTerm": search} if search else {}),
                },
            )
            items = payload.get("Items", [])
            all_items.extend(items)

            total = payload.get("TotalRecordCount", len(all_items))
            start_index += len(items)
            if not items or start_index >= total:
                break

        return all_items

    async def async_get_sessions(self) -> list[dict[str, Any]]:
        """Fetch current Jellyfin sessions."""
        return await self.async_get_json(
            "/Sessions",
            params={"ActiveWithinSeconds": 86400},
        )

    async def async_get_live_tv_channels(
        self,
        *,
        channel_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch live TV channels."""
        payload = await self.async_get_json(
            "/LiveTv/Channels",
            params={
                "AddCurrentProgram": "true",
                "EnableImages": "false",
                **({"Type": channel_type} if channel_type else {}),
                **({"Limit": limit} if limit is not None else {}),
            },
        )
        return payload.get("Items", [])

    async def async_get_live_tv_programs(
        self,
        *,
        channel_ids: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch live TV guide programs."""
        payload = await self.async_get_json(
            "/LiveTv/Programs",
            params={
                "EnableImages": "false",
                "EnableTotalRecordCount": "true",
                "SortBy": "StartDate",
                "SortOrder": "Ascending",
                **({"ChannelIds": ",".join(channel_ids)} if channel_ids else {}),
                **({"MinStartDate": start.isoformat()} if start else {}),
                **({"MaxEndDate": end.isoformat()} if end else {}),
                **({"Limit": limit} if limit is not None else {}),
            },
        )
        return payload.get("Items", [])

    async def async_get_guide_info(self) -> dict[str, Any]:
        """Fetch guide metadata."""
        return await self.async_get_json("/LiveTv/GuideInfo")

    async def async_play_media(
        self,
        session_id: str,
        item_id: str,
        *,
        play_command: str = "PlayNow",
        start_index: int | None = None,
    ) -> None:
        """Send a play instruction to a remote session."""
        params: dict[str, Any] = {
            "playCommand": play_command,
            "itemIds": item_id,
        }
        if start_index is not None:
            params["startIndex"] = start_index
        await self.async_post(f"/Sessions/{session_id}/Playing", params=params)

    async def async_send_playstate(self, session_id: str, command: str) -> None:
        """Send a playstate command to a session."""
        await self.async_post(f"/Sessions/{session_id}/Playing/{command}")
