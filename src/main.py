"""Entry point pipeline ingestion: orkestrasi sumber, manifest, dan upload."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src import storage
from src.config import DEFAULT_LOCATIONS, Settings, get_settings
from src.sources import air, firms, magma, owm, weather

FIXTURES = Path("tests/fixtures")


def utc_now() -> datetime:
    return datetime.now(UTC)


def write_json(path: Path, payload: object) -> dict:
    """Tulis JSON rapi dan kembalikan metadata berkas (ukuran + sha256)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    data = text.encode("utf-8")
    path.write_bytes(data)
    return {
        "file": path.as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def run_firms(settings: Settings, days: int, offline: bool) -> list[dict]:
    if offline:
        return firms.parse_hotspots(read_fixture("firms_sample.csv"))
    timeout = max(settings.request_timeout, 60)
    return firms.fetch_hotspots(settings.firms_map_key, days=days, timeout=timeout)


def run_air(settings: Settings, days: int, offline: bool) -> list[dict]:
    if offline:
        payload = json.loads(read_fixture("air_sample.json"))
        return [air.parse_air_quality(payload, "Jakarta")]
    return [
        air.fetch_air_quality(lat, lon, name, timeout=settings.request_timeout)
        for name, (lat, lon) in DEFAULT_LOCATIONS.items()
    ]


def run_weather(settings: Settings, days: int, offline: bool) -> list[dict]:
    if offline:
        payload = json.loads(read_fixture("weather_sample.json"))
        return [weather.parse_weather(payload, "Jakarta")]
    return [
        weather.fetch_weather(lat, lon, name, timeout=settings.request_timeout)
        for name, (lat, lon) in DEFAULT_LOCATIONS.items()
    ]


def run_owm(settings: Settings, days: int, offline: bool) -> list[dict]:
    if offline:
        payload = json.loads(read_fixture("owm_sample.json"))
        return [owm.parse_air_pollution(payload, "Jakarta")]
    return [
        owm.fetch_air_pollution(
            lat, lon, name, settings.owm_api_key, timeout=settings.request_timeout
        )
        for name, (lat, lon) in DEFAULT_LOCATIONS.items()
    ]


def run_magma(settings: Settings, days: int, offline: bool) -> list[dict]:
    if offline:
        return magma.parse_activity_table(read_fixture("magma_aktivitas_sample.html"))
    return magma.fetch_volcano_activity(timeout=settings.request_timeout)


SOURCES = {
    "firms": run_firms,
    "air": run_air,
    "weather": run_weather,
    "owm": run_owm,
    "magma": run_magma,
}


def github_context() -> dict:
    """Metadata run agar manifest bisa dilacak ke eksekusi Actions terkait."""
    return {
        "repository": os.getenv("GITHUB_REPOSITORY", "local"),
        "workflow": os.getenv("GITHUB_WORKFLOW", "local"),
        "event": os.getenv("GITHUB_EVENT_NAME", "manual"),
        "commit": os.getenv("GITHUB_SHA", "")[:7],
        "actor": os.getenv("GITHUB_ACTOR", os.getenv("USERNAME") or os.getenv("USER") or ""),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline ingestion TCBA")
    parser.add_argument(
        "--sources",
        default="all",
        help="all atau daftar dipisah koma: firms,air,weather,owm,magma",
    )
    parser.add_argument("--days", type=int, default=None, help="rentang hari data FIRMS (1-5)")
    parser.add_argument("--offline", action="store_true", help="pakai fixture, tanpa jaringan")
    parser.add_argument("--no-upload", action="store_true", help="jangan unggah ke Azure Blob")
    parser.add_argument("--out", type=Path, default=Path("data"), help="folder hasil ingestion")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    days = args.days if args.days is not None else settings.firms_days

    names = list(SOURCES) if args.sources == "all" else [n.strip() for n in args.sources.split(",")]
    unknown = [name for name in names if name not in SOURCES]
    if unknown:
        raise SystemExit(f"sumber tidak dikenal: {', '.join(unknown)}")

    started = utc_now()
    run_id = os.getenv("GITHUB_RUN_ID") or uuid.uuid4().hex[:12]
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    manifest: dict = {
        "run_id": run_id,
        "started_at": started.isoformat(),
        "mode": "offline" if args.offline else "live",
        "days": days,
        "context": github_context(),
        "sources": {},
    }

    for name in names:
        try:
            records = SOURCES[name](settings, days, args.offline)
        except RuntimeError as exc:
            manifest["sources"][name] = {"status": "skipped", "reason": str(exc)}
            print(f"[{name}] dilewati: {exc}")
            continue
        except Exception as exc:
            manifest["sources"][name] = {"status": "error", "reason": str(exc)}
            print(f"[{name}] gagal: {exc}")
            continue

        target = args.out / "processed" / f"{name}_{stamp}.json"
        info = write_json(target, records)
        manifest["sources"][name] = {"status": "ok", "records": len(records), **info}
        print(f"[{name}] {len(records)} record -> {target}")

    manifest["finished_at"] = utc_now().isoformat()
    target_prefix = f"runs/{stamp}_{run_id}"
    will_upload = not args.no_upload and bool(settings.storage_account)
    manifest["blob_prefix"] = target_prefix if will_upload else None
    manifest["storage"] = {
        "account": settings.storage_account or None,
        "container": settings.storage_container if will_upload else None,
    }
    write_json(args.out / "manifest.json", manifest)

    if will_upload:
        uploaded = storage.upload_directory(
            args.out, settings.storage_account, settings.storage_container, target_prefix
        )
        print(f"upload: {uploaded} berkas -> {settings.storage_container}/{target_prefix}")
    elif not args.no_upload:
        print("upload dilewati: AZURE_STORAGE_ACCOUNT kosong")

    statuses = {info["status"] for info in manifest["sources"].values()}
    return 0 if "ok" in statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
