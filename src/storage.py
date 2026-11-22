"""Pengiriman hasil ingestion ke Azure Blob Storage tanpa kredensial statis."""

from __future__ import annotations

from pathlib import Path


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

    uploaded = 0
    for path in sorted(local_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        blob_name = f"{prefix}/{path.relative_to(local_dir).as_posix()}"
        container_client.upload_blob(name=blob_name, data=path.read_bytes(), overwrite=True)
        uploaded += 1
    return uploaded
