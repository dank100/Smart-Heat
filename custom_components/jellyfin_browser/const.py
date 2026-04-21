"""Constants for the Jellyfin Browser integration."""

from datetime import timedelta

DOMAIN = "jellyfin_browser"
PLATFORMS = ["sensor", "media_player"]

CONF_API_KEY = "api_key"
CONF_SERVER_URL = "server_url"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_NAME = "Jellyfin"
DEFAULT_UPDATE_INTERVAL = 300
DEFAULT_SCAN_LIMIT = 200
MAX_ATTRIBUTE_ITEMS = 25
SCAN_PAGE_SIZE = 200
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_UPDATE_INTERVAL)

SERVICE_GET_CONTENT = "get_content"
SERVICE_GET_DEVICES = "get_devices"
SERVICE_GET_LIVE_TV_CHANNELS = "get_live_tv_channels"
SERVICE_GET_LIVE_TV_PROGRAMS = "get_live_tv_programs"
SERVICE_PLAY_ON_DEVICE = "play_on_device"
SERVICE_REFRESH = "refresh"

ATTR_CHANNEL_ID = "channel_id"
ATTR_CHANNEL_IDS = "channel_ids"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_END = "end"
ATTR_ITEM_ID = "item_id"
ATTR_ITEM_TYPES = "item_types"
ATTR_LIMIT = "limit"
ATTR_SEARCH = "search"
ATTR_SESSION_ID = "session_id"
ATTR_START = "start"

MEDIA_TYPES = [
    "Movie",
    "Series",
    "Episode",
    "MusicAlbum",
    "Audio",
    "Video",
]
