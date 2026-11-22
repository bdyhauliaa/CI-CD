"""Perkakas bersama untuk semua modul sumber: sesi HTTP dan helper data hourly."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "tcba-cicd-ingestion/1.0 (+https://github.com/bdyhauliaa/CI-CD)"


def build_session() -> requests.Session:
    """Sesi dengan User-Agent jelas dan retry untuk galat sementara."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


SESSION = build_session()


def latest_hourly(payload: dict) -> dict:
    """Ambil nilai terakhir dari blok ``hourly`` respons Open-Meteo."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    index = len(times) - 1
    values: dict = {"time": times[index] if index >= 0 else None}
    for field, series in hourly.items():
        if field != "time":
            values[field] = series[index] if 0 <= index < len(series) else None
    return values
