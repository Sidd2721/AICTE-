import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.domain.vault import get_vault_dir


def _upload_test_pdf(client: TestClient, headers: dict[str, str]) -> dict:
    pdf_bytes = b"%PDF-1.4 sample resilient vault content"
    file_obj = io.BytesIO(pdf_bytes)
    res = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"kind": "fdr_scan"},
        files={"file": ("resilience_test.pdf", file_obj, "application/pdf")},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_missing_vault_file_returns_clean_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing vault file on disk and in cloud returns clean 404, never 500."""
    monkeypatch.setattr(
        "app.integration.supabase_storage.is_supabase_configured",
        lambda: False,
    )
    doc_data = _upload_test_pdf(client, superuser_token_headers)
    doc_id = doc_data["id"]
    storage_key = doc_data["storage_key"]

    vault_file = get_vault_dir() / f"{storage_key}.enc"
    if vault_file.exists():
        vault_file.unlink()

    dl_res = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 404
    assert "Vault file not found" in dl_res.json()["detail"]


def test_missing_local_file_recovers_from_cloud_when_available(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """When ephemeral local disk loses file, system seamlessly falls back to cloud storage."""
    from app.integration.supabase_storage import is_supabase_configured

    if not is_supabase_configured():
        pytest.skip("Supabase not configured in this environment")

    doc_data = _upload_test_pdf(client, superuser_token_headers)
    doc_id = doc_data["id"]
    storage_key = doc_data["storage_key"]

    vault_file = get_vault_dir() / f"{storage_key}.enc"
    if vault_file.exists():
        vault_file.unlink()

    dl_res = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 200
    assert dl_res.content == b"%PDF-1.4 sample resilient vault content"


def test_corrupt_vault_file_returns_clean_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """Corrupted vault bytes return clean 404 instead of unhandled 500 error."""
    doc_data = _upload_test_pdf(client, superuser_token_headers)
    doc_id = doc_data["id"]
    storage_key = doc_data["storage_key"]

    vault_file = get_vault_dir() / f"{storage_key}.enc"
    assert vault_file.exists()
    # Write corrupt truncated payload (< 28 bytes)
    vault_file.write_bytes(b"corrupted-short-payload")

    dl_res = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 404
    assert "unreadable or corrupt" in dl_res.json()["detail"]


def test_vault_key_mismatch_returns_clean_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Key rotation or invalid decryption key returns clean 404 instead of 500."""
    doc_data = _upload_test_pdf(client, superuser_token_headers)
    doc_id = doc_data["id"]

    # Change VAULT_KEY to another valid 32-byte key
    monkeypatch.setattr(
        settings,
        "VAULT_KEY",
        "9ZkP2xL1mQ5vW3yA1cE6hJ8nM0oQ2sU4wX6zI4GjN7x=",
    )

    dl_res = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 404
    assert "unreadable or corrupt" in dl_res.json()["detail"]


def test_nonexistent_document_id_returns_404(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """Requesting an unknown document ID returns clean 404."""
    random_id = uuid.uuid4()
    dl_res = client.get(
        f"/api/v1/documents/{random_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 404
    assert "Document not found" in dl_res.json()["detail"]


def test_healthy_document_downloads_cleanly(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """Intact vault document downloads successfully with 200 and correct payload."""
    pdf_bytes = b"%PDF-1.4 sample resilient vault content"
    doc_data = _upload_test_pdf(client, superuser_token_headers)
    doc_id = doc_data["id"]

    dl_res = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_bytes
