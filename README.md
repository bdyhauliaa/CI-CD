# CI-CD — Pipeline Ingestion Data Kebakaran Hutan, Kualitas Udara & Aktivitas Vulkanik

[![CI](https://github.com/bdyhauliaa/CI-CD/actions/workflows/ci.yml/badge.svg)](https://github.com/bdyhauliaa/CI-CD/actions/workflows/ci.yml)
[![CD](https://github.com/bdyhauliaa/CI-CD/actions/workflows/cd.yml/badge.svg)](https://github.com/bdyhauliaa/CI-CD/actions/workflows/cd.yml)

Tugas pribadi mata kuliah **Teknologi Cloud untuk Big Data dan Data Analitik**:
implementasi CI/CD untuk pipeline ingestion data lingkungan Indonesia, memakai
**GitHub Actions** sebagai orkestrator dan **Azure Blob Storage** sebagai penyimpanan hasil.

---

## 1. Ringkasan

Pipeline mengambil data dari lima sumber, menormalkannya menjadi JSON, menulis
`manifest.json` sebagai catatan eksekusi, lalu mengunggah semuanya ke Azure Blob Storage
tanpa menyimpan kredensial statis (autentikasi **OIDC** ke Microsoft Entra ID).

| Sumber | Data | Metode | Kunci |
| --- | --- | --- | --- |
| NASA FIRMS | Titik panas (hotspot) kebakaran hutan & lahan | REST API (CSV) | `MAP_KEY` gratis |
| Open-Meteo Air Quality | PM2.5, PM10, CO, NO₂, SO₂, O₃, AQI | REST API (JSON) | tidak perlu |
| Open-Meteo Weather | Angin, suhu, kelembapan, curah hujan | REST API (JSON) | tidak perlu |
| OpenWeatherMap | AQI dan konsentrasi polutan (pembanding) | REST API (JSON) | API key |
| MAGMA Indonesia (PVMBG) | Aktivitas gunung api | Scraping HTML + fallback JSON | tidak perlu |

---

## 2. Alur

```text
        ┌───────────────────────── CI (push / pull_request) ─────────────────────────┐
        │  ruff check → pytest → run offline (fixture) → artifact + job summary      │
        └────────────────────────────────────────────────────────────────────────────┘
                                            │ merge ke main
                                            ▼
        ┌────────────────────── CD (push main / schedule / dispatch) ────────────────┐
        │  azure/login (OIDC) → src.main → data/processed + manifest.json            │
        │                    → upload ke container scraping-results → verifikasi     │
        └────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Struktur Repo

```text
.
├── .github/workflows/
│   ├── ci.yml                 # lint, test, smoke run, artifact
│   └── cd.yml                 # OIDC login, ingest, upload ke Azure Blob
├── src/
│   ├── config.py              # env, bounding box Indonesia, titik pantau
│   ├── main.py                # CLI + orkestrasi + manifest
│   ├── storage.py             # upload ke Azure Blob (DefaultAzureCredential)
│   └── sources/
│       ├── base.py            # sesi HTTP + retry + helper hourly
│       ├── firms.py           # NASA FIRMS
│       ├── air.py             # Open-Meteo Air Quality
│       ├── weather.py         # Open-Meteo Weather
│       ├── owm.py             # OpenWeatherMap Air Pollution
│       └── magma.py           # MAGMA Indonesia (scraping)
├── tests/
│   ├── test_parsers.py        # tes parser tanpa jaringan
│   └── fixtures/              # contoh respons tiap sumber
├── data/.gitkeep              # hasil run (di-ignore)
├── .env.example
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## 4. Menjalankan Lokal

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

cp .env.example .env               # isi key bila punya

ruff check . && ruff format --check .
pytest -q

# tanpa jaringan (memakai fixture)
python -m src.main --offline --out data

# data nyata, tanpa upload
python -m src.main --sources all --days 5 --no-upload

# data nyata + upload ke Azure (butuh `az login` sebagai ganti OIDC)
python -m src.main --days 5
```

Contoh keluaran:

```text
[firms] 295 record -> data/processed/firms_20261122T072048Z.json
[air] 5 record -> data/processed/air_20261122T072048Z.json
[weather] 5 record -> data/processed/weather_20261122T072048Z.json
[owm] 5 record -> data/processed/owm_20261122T072048Z.json
[magma] 69 record -> data/processed/magma_20261122T072048Z.json
upload: 6 berkas -> scraping-results/runs/20261122T072048Z_1234567890
```

---

## 5. Konfigurasi

| Nama | Jenis di GitHub | Keterangan |
| --- | --- | --- |
| `NASA_FIRMS_MAP_KEY` | Secret | MAP_KEY gratis dari FIRMS |
| `OPENWEATHER_API_KEY` | Secret | API key OpenWeatherMap |
| `AZURE_CLIENT_ID` | Variable | Application (client) ID |
| `AZURE_TENANT_ID` | Variable | Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Variable | Subscription ID |
| `AZURE_STORAGE_ACCOUNT` | Variable | mis. `implementasicicd1` |
| `AZURE_STORAGE_CONTAINER` | Variable | `scraping-results` |

Untuk lokal, isi nilai yang sama di `.env` (sudah di-`.gitignore`).

---

## 6. Perilaku Status Sumber

| Kondisi | Status di manifest | Dampak ke pipeline |
| --- | --- | --- |
| Berhasil | `ok` | lanjut |
| Kunci API kosong | `skipped` | tetap hijau |
| Jaringan/parsing gagal | `error` + alasan | tetap hijau selama ada satu sumber `ok` |

Exit code hanya `1` jika **semua** sumber gagal, sehingga satu penyedia yang sedang
bermasalah tidak menjatuhkan proses deployment.

---

## 7. Skema Data

`data/manifest.json`

```json
{
  "run_id": "1234567890",
  "started_at": "2026-11-22T01:02:03+00:00",
  "finished_at": "2026-11-22T01:02:41+00:00",
  "mode": "live",
  "days": 5,
  "context": {
    "repository": "bdyhauliaa/CI-CD",
    "workflow": "CD",
    "event": "schedule",
    "commit": "1a2b3c4",
    "actor": "bdyhauliaa"
  },
  "sources": {
    "firms": {
      "status": "ok",
      "records": 292,
      "file": "data/processed/firms_20261122T010203Z.json",
      "bytes": 51234,
      "sha256": "…"
    }
  }
}
```

Susunan di Azure Blob Storage:

```text
scraping-results/
└── runs/20261122T010203Z_1234567890/
    ├── manifest.json
    └── processed/
        ├── air_20261122T010203Z.json
        ├── firms_20261122T010203Z.json
        ├── magma_20261122T010203Z.json
        └── weather_20261122T010203Z.json
```

---

## 8. Workflow

| Workflow | Trigger | Isi |
| --- | --- | --- |
| `ci.yml` | `push` & `pull_request` ke `dev`/`main`, `workflow_dispatch` | ruff, pytest, smoke run offline, artifact |
| `cd.yml` | `push` ke `main`, `schedule` (`0 21 * * *` = 04.00 WIB), `workflow_dispatch` | OIDC login, ingestion, upload, verifikasi blob |

Konfigurasi Azure (resource group, storage account, app registration, federated credential,
dan role) mengikuti langkah pada laporan tugas.

---

## 9. Catatan

- Data FIRMS memakai sensor **MODIS_NRT** dengan fallback **VIIRS_SNPP_NRT**; cakupan
  VIIRS untuk Indonesia kadang kosong, sedangkan MODIS lebih stabil.
- Waktu `schedule` memakai UTC, bukan WIB.
- Data yang diunduh adalah ringkasan, bukan pengganti data resmi instansi terkait.
