"""Sumber NASA FIRMS: titik panas kebakaran hutan dan lahan."""

from __future__ import annotations

import csv
import io

from src.config import INDONESIA_BBOX
from src.sources.base import SESSION

FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# MODIS dijadikan default karena cakupan hariannya lebih stabil untuk Indonesia;
# VIIRS dipakai sebagai cadangan bila MODIS tidak mengembalikan deteksi.
DEFAULT_SENSORS = ("MODIS_NRT", "VIIRS_SNPP_NRT")


def fetch_hotspots(
    map_key: str,
    days: int = 1,
    sensors: tuple[str, ...] = DEFAULT_SENSORS,
) -> list[dict]:
    """Ambil hotspot dari Area API, mencoba sensor berikutnya bila kosong."""
    if not map_key:
        raise RuntimeError("NASA_FIRMS_MAP_KEY belum diisi")

    bbox = ",".join(f"{value:g}" for value in INDONESIA_BBOX)
    for sensor in sensors:
        url = f"{FIRMS_URL}/{map_key}/{sensor}/{bbox}/{days}"
        response = SESSION.get(url, timeout=90)
        response.raise_for_status()
        head = response.text[:200]
        if "Invalid" in head:
            raise RuntimeError("FIRMS menolak MAP_KEY, periksa kembali nilai secret")
        if "No data" in head:
            continue
        records = parse_hotspots(response.text, sensor)
        if records:
            return records
    return []


def parse_hotspots(payload: str, sensor: str = DEFAULT_SENSORS[0]) -> list[dict]:
    """Ubah CSV FIRMS menjadi daftar record yang seragam."""
    records: list[dict] = []
    for row in csv.DictReader(io.StringIO(payload)):
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        records.append(
            {
                "source": "nasa_firms",
                "sensor": sensor,
                "latitude": latitude,
                "longitude": longitude,
                "acq_date": row.get("acq_date", ""),
                "acq_time": row.get("acq_time", ""),
                "confidence": row.get("confidence", ""),
                "frp": row.get("frp") or None,
            }
        )
    return records
