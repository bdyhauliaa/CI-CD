"""Sumber Open-Meteo Weather: angin, suhu, kelembapan, dan curah hujan."""

from __future__ import annotations

from src.sources.base import SESSION, latest_hourly

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"


def fetch_weather(latitude: float, longitude: float, location: str, timeout: int = 30) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY,
        "timezone": "Asia/Jakarta",
        "forecast_days": 1,
    }
    response = SESSION.get(WEATHER_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return parse_weather(response.json(), location)


def parse_weather(payload: dict, location: str) -> dict:
    return {
        "source": "open_meteo_weather",
        "location": location,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        **latest_hourly(payload),
    }
