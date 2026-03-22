"""Constants for Wavin Smart Heat."""

DOMAIN = "wavin_smart_heat"
PLATFORMS = ["sensor", "number"]

CONF_ROOMS = "rooms"
CONF_ROOM_NAME = "room_name"
CONF_AREA_ID = "area_id"
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_TEMP_SENSOR = "temp_sensor"
CONF_LIGHT_ENTITIES = "light_entities"
CONF_OCCUPANCY_ENTITIES = "occupancy_entities"
CONF_WINDOW_SENSORS = "window_sensors"
CONF_EXTRA_SENSORS = "extra_sensors"
CONF_DAY_TEMP = "day_temp"
CONF_NIGHT_TEMP = "night_temp"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_MORNING_TEMP = "morning_temp"

CONF_WEATHER_ENTITY = "weather_entity"
CONF_SUN_ENTITY = "sun_entity"
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_SUN_ELEVATION_SENSOR = "sun_elevation_sensor"
CONF_UV_SENSOR = "uv_sensor"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_LEARNING_RATE = "learning_rate"
CONF_APPLY_CHANGES = "apply_changes"

DEFAULT_UPDATE_INTERVAL = 600
DEFAULT_LEARNING_RATE = 0.02
DEFAULT_MIN_TEMP = 17.0
DEFAULT_MAX_TEMP = 24.0

STORAGE_KEY = f"{DOMAIN}_model"
STORAGE_VERSION = 1
