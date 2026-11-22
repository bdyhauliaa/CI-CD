"""Tes parser dan helper memakai fixture, sehingga tidak butuh jaringan maupun API key."""

import json
from pathlib import Path

from src.main import write_json
from src.sources import air, firms, magma, owm, weather
from src.storage import iter_upload_files

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_hotspots_reads_coordinates() -> None:
    payload = (FIXTURES / "firms_sample.csv").read_text(encoding="utf-8")
    records = firms.parse_hotspots(payload, sensor="MODIS_NRT")

    assert len(records) == 2
    assert records[0]["latitude"] == 0.512
    assert records[0]["source"] == "nasa_firms"
    assert records[0]["sensor"] == "MODIS_NRT"


def test_parse_hotspots_skips_incomplete_rows() -> None:
    payload = "latitude,longitude\n-2.9,\n,106.8\n"
    assert firms.parse_hotspots(payload) == []


def test_air_quality_uses_latest_hour() -> None:
    payload = json.loads((FIXTURES / "air_sample.json").read_text(encoding="utf-8"))
    record = air.parse_air_quality(payload, "Jakarta")

    assert record["location"] == "Jakarta"
    assert record["pm2_5"] == 15.0
    assert record["us_aqi"] == 52


def test_magma_activity_table_is_scraped() -> None:
    html = (FIXTURES / "magma_aktivitas_sample.html").read_text(encoding="utf-8")
    records = magma.parse_activity_table(html)

    assert len(records) == 2
    assert records[0]["volcano"] == "Semeru"
    assert records[0]["province"] == "Jawa Timur"
    assert records[0]["level"] == "III"
    assert records[1]["level_name"] == "Waspada"


def test_magma_generic_table_fallback() -> None:
    html = (FIXTURES / "magma_sample.html").read_text(encoding="utf-8")
    records = magma.parse_html_table(html)

    assert len(records) == 1
    assert records[0]["raw"]["gunung"] == "Merapi"


def test_parse_weather_uses_latest_hour() -> None:
    payload = json.loads((FIXTURES / "weather_sample.json").read_text(encoding="utf-8"))
    record = weather.parse_weather(payload, "Jakarta")

    assert record["location"] == "Jakarta"
    assert record["temperature_2m"] == 27.8
    assert record["wind_speed_10m"] == 6.1


def test_parse_owm_air_pollution_components() -> None:
    payload = json.loads((FIXTURES / "owm_sample.json").read_text(encoding="utf-8"))
    record = owm.parse_air_pollution(payload, "Jakarta")

    assert record["aqi_index"] == 2
    assert record["pm2_5"] == 14.7
    assert record["ozone"] == 96.2


def test_write_json_records_metadata(tmp_path) -> None:
    target = tmp_path / "processed" / "sample.json"
    info = write_json(target, [{"source": "test"}])

    assert target.exists()
    assert info["bytes"] > 0
    assert len(info["sha256"]) == 64
    assert info["file"].endswith("sample.json")


def test_iter_upload_files_skips_hidden(tmp_path) -> None:
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "firms.json").write_text("[]", encoding="utf-8")

    files = iter_upload_files(tmp_path)

    assert [path.name for path in files] == ["manifest.json", "firms.json"]
