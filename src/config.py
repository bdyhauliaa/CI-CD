"""Konfigurasi terpusat: environment, wilayah pantau, dan parameter run."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Bounding box Indonesia: barat, selatan, timur, utara
INDONESIA_BBOX = (94.0, -11.0, 141.0, 6.0)

# Titik pantau kualitas udara & cuaca (nama: (latitude, longitude))
DEFAULT_LOCATIONS = {
    "Jakarta": (-6.2088, 106.8456),
    "Palembang": (-2.9761, 104.7754),
    "Pekanbaru": (0.5071, 101.4478),
    "Pontianak": (-0.0263, 109.3425),
    "Banjarmasin": (-3.3186, 114.5944),
}


@dataclass(frozen=True)
class Settings:
    """Nilai konfigurasi yang dibaca sekali per eksekusi."""

    firms_map_key: str
    owm_api_key: str
    storage_account: str
    storage_container: str
    firms_days: int
    request_timeout: int


def get_settings() -> Settings:
    """Baca konfigurasi dari environment (atau file .env saat lokal)."""
    return Settings(
        firms_map_key=os.getenv("NASA_FIRMS_MAP_KEY", "").strip(),
        owm_api_key=os.getenv("OPENWEATHER_API_KEY", "").strip(),
        storage_account=os.getenv("AZURE_STORAGE_ACCOUNT", "").strip(),
        storage_container=os.getenv("AZURE_STORAGE_CONTAINER", "scraping-results").strip(),
        firms_days=int(os.getenv("FIRMS_DAYS", "1")),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
    )
