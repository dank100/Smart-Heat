# Home Assistant Custom Integrations

This repository contains Home Assistant custom integrations that can be installed through HACS as a custom repository.

## HACS Installation
1. Open HACS in Home Assistant.
2. Add this repository as a **Custom Repository** with type **Integration**.
3. Install the integration you want from HACS.
4. Restart Home Assistant.
5. Add the integration from **Settings -> Devices & services**.

## Included Integrations

### Wavin Smart Heat

Smart, predictive heating control for Wavin/ESPHome setups in Home Assistant.

## Features
- Multi-room setup wizard
- Predictive target temperatures (online learning)
- Weather, sun elevation, UV, wind, and cloud coverage inputs
- Optional sleep end time preheat
- Auto-apply recommendations on a schedule
- Confidence sensor + data source transparency

## Configuration
The setup wizard lets you configure per-room entities and schedules. You can leave the weather entity blank; it will automatically use the first available `weather.*` entity.

### Required per room
- Climate entity
- Temperature sensor
- Day/Night target temperatures

### Optional
- Room wake time
- Lights (to suppress sleep preheat)
- Extra sensors (added as ML features)

## Services
- `wavin_smart_heat.apply_recommendations` — apply current recommended targets to all rooms.

## Notes
- Prediction confidence increases as more samples are collected.
- Weather data is pulled from the selected `weather.*` entity (OpenWeatherMap recommended for UV and cloud coverage).

## Support
Open an issue or start a discussion in this repository.

### Jellyfin Browser

This repository also includes a `jellyfin_browser` custom integration for Home Assistant.

#### Features
- Config flow for Jellyfin server URL and API key
- Library summary sensor and cast-device summary sensor
- Live TV summary sensor plus Live TV channel and program services
- Services to list content and active cast-capable devices
- `media_player` entities for remote-controllable Jellyfin sessions

#### Example services
- `jellyfin_browser.get_content`
- `jellyfin_browser.get_devices`
- `jellyfin_browser.get_live_tv_channels`
- `jellyfin_browser.get_live_tv_programs`
- `jellyfin_browser.play_on_device`
