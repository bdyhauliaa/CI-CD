"""Sumber MAGMA Indonesia (PVMBG): aktivitas gunung api via JSON atau scraping HTML."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from src.sources.base import SESSION

MAGMA_JSON_URL = "https://magma.esdm.go.id/v1/gunung-api/aktivitas"
MAGMA_ACTIVITY_URL = "https://magma.esdm.go.id/v1/gunung-api/tingkat-aktivitas"
MAGMA_PAGE_URL = "https://magma.esdm.go.id/"

LEVEL_PATTERN = re.compile(r"Level\s+(IV|III|II|I)\s*\(([^)]+)\)")


def fetch_volcano_activity(timeout: int = 30) -> list[dict]:
    """Coba endpoint JSON; bila tidak tersedia, scraping tabel tingkat aktivitas."""
    try:
        response = SESSION.get(MAGMA_JSON_URL, timeout=timeout)
        if response.ok and "json" in response.headers.get("Content-Type", ""):
            records = parse_json_activity(response.json())
            if records:
                return records
    except Exception:
        pass

    response = SESSION.get(MAGMA_ACTIVITY_URL, timeout=timeout)
    response.raise_for_status()
    records = parse_activity_table(response.text)
    if records:
        return records

    # Cadangan terakhir: tabel generik pada beranda.
    response = SESSION.get(MAGMA_PAGE_URL, timeout=timeout)
    response.raise_for_status()
    return parse_html_table(response.text)


def parse_activity_table(html: str) -> list[dict]:
    """Urai tabel tingkat aktivitas: baris level diikuti baris nama gunung api."""
    table = BeautifulSoup(html, "html.parser").find("table")
    if table is None:
        return []

    records: list[dict] = []
    level, level_name = "", ""

    for row in table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue

        match = LEVEL_PATTERN.search(cells[0])
        if match:
            level, level_name = match.group(1), match.group(2)
            continue

        if len(cells) == 1:
            text = cells[0].replace("Lihat laporan", "").strip(" -")
            if not text or text.lower().startswith("tidak ada gunung api"):
                continue
            name, _, province = text.partition(" - ")
            records.append(
                {
                    "source": "magma",
                    "volcano": name.strip(),
                    "province": province.strip(),
                    "level": level,
                    "level_name": level_name,
                }
            )
    return records


def parse_json_activity(payload: object) -> list[dict]:
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    records: list[dict] = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict):
            records.append(
                {
                    "source": "magma",
                    "volcano": item.get("nama") or item.get("name") or "",
                    "level": item.get("status") or item.get("level") or "",
                    "updated_at": item.get("updated_at") or item.get("created_at") or "",
                }
            )
    return records


def parse_html_table(html: str) -> list[dict]:
    """Ambil tabel pertama pada halaman dan ubah setiap baris menjadi dict."""
    table = BeautifulSoup(html, "html.parser").find("table")
    if table is None:
        return []
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []
    headers = [cell.get_text(" ", strip=True).lower() for cell in rows[0].find_all(["th", "td"])]
    records: list[dict] = []
    for row in rows[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if cells:
            records.append({"source": "magma", "raw": dict(zip(headers, cells, strict=False))})
    return records
