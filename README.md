# Implementasi CI-CD 

Pipeline pengambilan data titik panas kebakaran hutan, kualitas udara, cuaca, dan aktivitas
gunung api. Setiap perubahan kode diuji otomatis lewat **GitHub Actions** (CI), lalu hasil
ingestion dikirim otomatis ke **Azure Blob Storage** (CD) memakai autentikasi **OIDC** —
tanpa kredensial statis di dalam repo.

## Sumber Data

| Sumber | Data | Kunci |
| --- | --- | --- |
| NASA FIRMS | Titik panas (hotspot) kebakaran | `MAP_KEY` gratis |
| Open-Meteo Air Quality | PM2.5, PM10, CO, NO₂, SO₂, O₃, AQI | tidak perlu |
| Open-Meteo Weather | Angin, suhu, kelembapan, hujan | tidak perlu |
| OpenWeatherMap | AQI dan polutan (pembanding) | API key |
| MAGMA Indonesia | Aktivitas gunung api (scraping) | tidak perlu |

## Alur

```text
CI   push / pull_request (dev, main)  →  ruff → pytest → smoke run offline → artifact
CD   push main · jadwal 04.00 WIB · manual
     → azure/login (OIDC) → ingestion → upload ke Azure Blob → verifikasi blob
```

## Struktur

```text
├── .github/workflows/   ci.yml · cd.yml
├── src/                 config.py · main.py · storage.py
│   └── sources/         base.py · firms.py · air.py · weather.py · owm.py · magma.py
├── tests/               test_parsers.py + fixtures/
├── data/.gitkeep        hasil run (di-ignore)
└── README.md · pyproject.toml · requirements*.txt · .env.example
```

## Cara Menjalankan

### Prasyarat

- **Python 3.12+**
- Untuk upload ke Azure: `az login` (lokal) — di GitHub Actions ditangani `azure/login`

### Persiapan

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env               # isi API key bila punya
```

### Menjalankan pipeline

```bash
# 1. tanpa jaringan, memakai fixture (dipakai CI)
python -m src.main --offline --out data

# 2. data nyata tanpa upload
python -m src.main --days 5 --no-upload

# 3. data nyata + upload ke Azure Blob
python -m src.main --days 5
```

| Opsi | Fungsi |
| --- | --- |
| `--sources all` | semua sumber, atau `firms,air,weather,owm,magma` |
| `--days 5` | rentang hari data FIRMS (1–5) |
| `--offline` | pakai fixture, tanpa koneksi internet |
| `--no-upload` | lewati pengiriman ke Azure |
| `--out data` | folder keluaran |

Hasil: `data/processed/<sumber>_<timestamp>.json` dan `data/manifest.json`.

### Pemeriksaan kode

```bash
ruff check . && ruff format --check .
pytest -q
```

## Konfigurasi

| Nama | Jenis di GitHub | Keterangan |
| --- | --- | --- |
| `NASA_FIRMS_MAP_KEY` | Secret | MAP_KEY dari FIRMS |
| `OPENWEATHER_API_KEY` | Secret | API key OpenWeatherMap |
| `AZURE_CLIENT_ID` | Variable | Application (client) ID |
| `AZURE_TENANT_ID` | Variable | Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Variable | Subscription ID |
| `AZURE_STORAGE_ACCOUNT` | Variable | `implementasicicd1` |
| `AZURE_STORAGE_CONTAINER` | Variable | `scraping` |

Untuk lokal, nilai yang sama diisi di `.env` (sudah di-`.gitignore`).

## CI/CD

| Workflow | Trigger | Isi |
| --- | --- | --- |
| `ci.yml` | `push` & `pull_request` ke `dev`/`main` | ruff, pytest, smoke run offline, artifact |
| `cd.yml` | `push` ke `main`, `schedule`, `workflow_dispatch` | OIDC login, ingestion, upload, verifikasi blob |

Merge ke `main` hanya dapat dilakukan jika status check **Lint, Test & Smoke Run** lolos
(branch protection), sehingga CD tidak pernah menerima kode yang gagal CI.

Jadwal CD: `0 21 * * *` (UTC) = **04.00 WIB** setiap hari, bisa juga dijalankan manual dari
tab **Actions** dengan input `sources` dan `days`.

Hasil upload tersimpan per eksekusi, sehingga run baru tidak menimpa run sebelumnya:

```text
scraping/runs/<waktu>_<run_id>/
├── manifest.json
└── processed/{air,firms,magma,owm,weather}_<waktu>.json
```

## Catatan

- FIRMS memakai sensor **MODIS_NRT** dengan fallback **VIIRS_SNPP_NRT**.
- Data ditulis bertahap per sumber; sumber yang gagal dicatat di `manifest.json` dan tidak
  menggagalkan seluruh pipeline.
