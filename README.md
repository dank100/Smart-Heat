# Wavin Smart Heat (Home Assistant)

Smart, predictive heating control for Wavin/ESPHome setups in Home Assistant.

## Features
- Multi-room setup wizard
- Predictive target temperatures (online learning)
- Weather, sun elevation, UV, wind, and cloud coverage inputs
- Optional sleep end time preheat
- Auto-apply recommendations on a schedule
- Confidence sensor + data source transparency

## Installation (HACS)
1. Add this repository to HACS as a **Custom Repository** (Integration).
2. Install **Wavin Smart Heat**.
3. Restart Home Assistant.
4. Add the integration via **Settings → Devices & services**.

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
