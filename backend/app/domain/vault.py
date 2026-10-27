import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

VAULT_DIR = Path(__file__).resolve().parent.parent / "vault"


def get_vault_key() -> bytes:
    raw = settings.VAULT_KEY.strip() if settings.VAULT_KEY else ""
    if not raw:
        raw = settings.SECRET_KEY
    try:
        decoded = base64.b64decode(raw)
        if len(decoded) in (16, 24, 32):
            return decoded
    except Exception:
        pass
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt data using AES-256-GCM with a random 12-byte nonce."""
    key = get_vault_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def decrypt_bytes(payload: bytes) -> bytes:
    """Decrypt payload (12-byte nonce + ciphertext + tag) using AES-256-GCM."""
    if len(payload) < 28:
        raise ValueError("Invalid encrypted payload: too short")
    key = get_vault_key()
    aesgcm = AESGCM(key)
    nonce = payload[:12]
    ciphertext = payload[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)


def sniff_magic_bytes(data: bytes) -> str:
    """Check genuine file headers for PDF, PNG, and JPEG."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise ValueError(
        "Invalid file content: file does not match genuine PDF or image format"
    )


def detect_dsc(data: bytes, mime_type: str) -> bool:
    """Detect presence of Digital Signature Certificate in PDF."""
    if mime_type == "application/pdf":
        return b"/ByteRange" in data and (b"/Contents" in data or b"/Sig" in data)
    return False


def store_in_vault(storage_key: str, data: bytes) -> Path:
    """Encrypt and store data in the vault directory and Supabase Storage."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    target_path = VAULT_DIR / f"{storage_key}.enc"
    encrypted = encrypt_bytes(data)
    target_path.write_bytes(encrypted)

    # Cloud Persistence: upload to Supabase Storage if configured
    try:
        from app.integration.supabase_storage import (
            is_supabase_configured,
            upload_to_supabase_vault,
        )

        if is_supabase_configured():
            upload_to_supabase_vault(f"{storage_key}.enc", encrypted)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Supabase vault upload skipped: %s", exc)

    return target_path


def read_from_vault(storage_key: str) -> bytes:
    """Read and decrypt data from local vault directory or Supabase Storage."""
    target_path = VAULT_DIR / f"{storage_key}.enc"
    if target_path.exists():
        encrypted = target_path.read_bytes()
        return decrypt_bytes(encrypted)

    # Fallback: attempt download from Supabase Storage
    try:
        from app.integration.supabase_storage import (
            download_from_supabase_vault,
            is_supabase_configured,
        )

        if is_supabase_configured():
            encrypted = download_from_supabase_vault(f"{storage_key}.enc")
            # Cache locally
            target_path.write_bytes(encrypted)
            return decrypt_bytes(encrypted)
    except Exception:
        pass

    raise FileNotFoundError(f"Vault key {storage_key} not found")
