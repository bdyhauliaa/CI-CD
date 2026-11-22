"""Pengiriman hasil ingestion ke Azure Blob Storage tanpa kredensial statis."""

from __future__ import annotations

from pathlib import Path


def iter_upload_files(root: Path) -> list[Path]:
    """Berkas yang akan diunggah; berkas tersembunyi seperti .gitkeep dilewati."""
    return [
        path for path in sorted(root.rglob("*")) if path.is_file() and not path.name.startswith(".")
    ]


def upload_directory(local_dir: Path, account: str, container: str, prefix: str) -> int:
    """Unggah seluruh berkas di ``local_dir`` ke ``container/prefix``.

    Autentikasi memakai DefaultAzureCredential, sehingga di GitHub Actions
    memanfaatkan sesi Azure CLI hasil langkah ``azure/login`` (OIDC).
    """
    if not account:
        raise RuntimeError("AZURE_STORAGE_ACCOUNT belum diisi")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )
    container_client = service.get_container_client(container)

    files = iter_upload_files(local_dir)
    for path in files:
        blob_name = f"{prefix}/{path.relative_to(local_dir).as_posix()}"
        container_client.upload_blob(name=blob_name, data=path.read_bytes(), overwrite=True)
    return len(files)
