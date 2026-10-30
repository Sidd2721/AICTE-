"""Encrypted document vault using AES-256-GCM envelope encryption.

SECURITY AND IMMUTABILITY RULES (FT3):
- The vault directory is configurable via the VAULT_PATH environment variable (defaults to ./vault).
- At start, the directory must be verified writable by the application process.
- Missing or non-distinct VAULT_KEY: logs a loud warning in development/demo, and strictly refuses
  to start in production.
- Key Immutability: Never rotate or re-encrypt existing documents automatically. Changing VAULT_KEY
  will render all previously stored documents permanently unreadable!
"""

import base64
import hashlib
import logging
import os
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_vault_dir() -> Path:
    """Return the configured vault directory or default to ./vault.

    Configurable via the VAULT_PATH environment variable.
    """
    if settings.VAULT_PATH and settings.VAULT_PATH.strip():
        return Path(settings.VAULT_PATH.strip()).resolve()
    return Path(__file__).resolve().parent.parent / "vault"


# Backward-compatible module-level reference
VAULT_DIR = get_vault_dir()


def validate_vault_security(env: str | None = None) -> None:
    """Validate vault key configuration and immutability rules at startup.

    Rules:
    - Missing or identical vault key: loud warning in demo, refuse to start in production.
    - Never rotate or re-encrypt anything.
    - Changing the key makes existing files permanently unreadable.
    """
    current_env = env or settings.FASTAPI_ENV
    vault_raw = settings.VAULT_KEY.strip() if settings.VAULT_KEY else ""
    secret_raw = settings.SECRET_KEY.strip() if settings.SECRET_KEY else ""

    if not vault_raw:
        msg = (
            "CRITICAL SECURITY WARNING: VAULT_KEY is unset! Falling back to SECRET_KEY. "
            "Changing or rotating this key later will render all previously stored documents permanently unreadable."
        )
        if current_env == "production":
            raise RuntimeError(f"Production startup aborted: {msg}")
        logger.warning(
            "****************************************************************"
        )
        logger.warning(msg)
        logger.warning(
            "****************************************************************"
        )
        return

    if vault_raw == secret_raw:
        msg = (
            "SECURITY NOTICE: VAULT_KEY is identical to SECRET_KEY. "
            "In production, a dedicated separate key must be used for AES-256-GCM vault encryption."
        )
        if current_env == "production":
            raise RuntimeError(f"Production startup aborted: {msg}")
        logger.warning(msg)


def check_vault_writable(vault_path: Path | None = None) -> bool:
    """Verify that the vault directory exists (or can be created) and is writable by the app user."""
    target_dir = vault_path or get_vault_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        probe_file = target_dir / f".write_probe_{uuid.uuid4().hex[:8]}"
        probe_file.write_bytes(b"probe")
        probe_file.unlink()
        return True
    except Exception as e:
        logger.error("Vault directory '%s' is not writable: %s", target_dir, e)
        return False


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
    vault_dir = get_vault_dir()
    vault_dir.mkdir(parents=True, exist_ok=True)
    target_path = vault_dir / f"{storage_key}.enc"
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
        logger.warning("Supabase vault upload skipped: %s", exc)

    return target_path


def read_from_vault(storage_key: str) -> bytes:
    """Read and decrypt data from local vault directory or Supabase Storage."""
    vault_dir = get_vault_dir()
    target_path = vault_dir / f"{storage_key}.enc"
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
