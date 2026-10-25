import io
from datetime import date, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.db import engine
from app.domain.vault import encrypt_bytes, decrypt_bytes, sniff_magic_bytes
from app.main import app
from app.models import Institution, User
from tests.utils.utils import get_superuser_token_headers

client = TestClient(app)


def test_vault_encryption_roundtrip() -> None:
    data = b"%PDF-1.4 test encrypted content"
    enc = encrypt_bytes(data)
    assert enc != data
    dec = decrypt_bytes(enc)
    assert dec == data


def test_magic_bytes_sniffing() -> None:
    # Valid PDF
    assert sniff_magic_bytes(b"%PDF-1.7\n...") == "application/pdf"
    # Valid PNG
    assert sniff_magic_bytes(b"\x89PNG\r\n\x1a\n\x00\x00") == "image/png"
    # Valid JPEG
    assert sniff_magic_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "image/jpeg"
    # Invalid
    try:
        sniff_magic_bytes(b"<html>not a doc</html>")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid file content" in str(e)


def test_document_upload_and_download(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    # Create valid fake PDF
    pdf_bytes = b"%PDF-1.4 fake pdf binary data"
    file_obj = io.BytesIO(pdf_bytes)

    upload_res = client.post(
        "/api/v1/documents/upload",
        headers=superuser_token_headers,
        data={"kind": "fdr_scan"},
        files={"file": ("fdr_scan.pdf", file_obj, "application/pdf")},
    )
    assert upload_res.status_code == 200, upload_res.text
    doc_data = upload_res.json()
    assert doc_data["kind"] == "fdr_scan"
    assert doc_data["mime"] == "application/pdf"
    doc_id = doc_data["id"]

    # Download decrypted document
    dl_res = client.get(
        f"/api/v1/documents/{doc_id}",
        headers=superuser_token_headers,
    )
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_bytes


def test_instrument_submit_and_list(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    today_val = date.today()
    maturity_val = today_val + timedelta(days=3650)

    sub_res = client.post(
        "/api/v1/instruments/submit",
        headers=superuser_token_headers,
        json={
            "ref_no": "FDR-2026-TEST-001",
            "bank_code": "SBI",
            "ifsc": "SBIN0001234",
            "amount_paise": 50000000,
            "issue_date": today_val.isoformat(),
            "maturity_date": maturity_val.isoformat(),
            "kind": "FDR",
        },
    )
    assert sub_res.status_code == 200, sub_res.text
    inst_data = sub_res.json()
    assert inst_data["ref_no"] == "FDR-2026-TEST-001"
    assert inst_data["amount_paise"] == 50000000
    assert inst_data["badge"] in ("claimed", "confirmed")
    assert "next_action_code" in inst_data

    # List instruments
    list_res = client.get(
        "/api/v1/instruments",
        headers=superuser_token_headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["count"] >= 1
    refs = [i["ref_no"] for i in list_data["data"]]
    assert "FDR-2026-TEST-001" in refs

