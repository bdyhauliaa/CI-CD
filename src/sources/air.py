"""Sumber Open-Meteo Air Quality: konsentrasi polutan dan indeks kualitas udara."""

from __future__ import annotations

from src.sources.base import SESSION, latest_hourly

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
HOURLY = "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi"


def fetch_air_quality(latitude: float, longitude: float, location: str) -> dict:
    """Ambil satu titik lokasi, kembalikan jam terakhir yang tersedia."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY,
        "timezone": "Asia/Jakarta",
        "forecast_days": 1,
    }
    response = SESSION.get(AIR_URL, params=params, timeout=30)
    response.raise_for_status()
    return parse_air_quality(response.json(), location)


def parse_air_quality(payload: dict, location: str) -> dict:
    return {
        "source": "open_meteo_air",
        "location": location,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        **latest_hourly(payload),
    }
