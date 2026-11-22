"""Sumber OpenWeatherMap Air Pollution sebagai pembanding kualitas udara."""

from __future__ import annotations

from src.sources.base import SESSION

OWM_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def fetch_air_pollution(latitude: float, longitude: float, location: str, api_key: str) -> dict:
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY belum diisi")
    params = {"lat": latitude, "lon": longitude, "appid": api_key}
    response = SESSION.get(OWM_URL, params=params, timeout=30)
    response.raise_for_status()
    return parse_air_pollution(response.json(), location)


def parse_air_pollution(payload: dict, location: str) -> dict:
    item = (payload.get("list") or [{}])[0]
    components = item.get("components") or {}
    return {
        "source": "openweathermap",
        "location": location,
        "aqi_index": (item.get("main") or {}).get("aqi"),
        "pm2_5": components.get("pm2_5"),
        "pm10": components.get("pm10"),
        "carbon_monoxide": components.get("co"),
        "nitrogen_dioxide": components.get("no2"),
        "sulphur_dioxide": components.get("so2"),
        "ozone": components.get("o3"),
    }
