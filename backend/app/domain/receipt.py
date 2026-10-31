"""Cryptographically signed release receipt issuance and verification (Invariant I8 / I9).

Algorithm: RS256 (RSA 2048-bit keypair) with short thumbprint key ID (kid) in token header.
Key resolution hierarchy:
  (a) Explicit environment variable RECEIPT_PRIVATE_KEY_PEM (Render secrets / production).
  (b) In demo/development, stable disk file or deterministic derivation.
  (c) Otherwise ephemeral with loud warning in demo, and hard startup abort in production.
"""

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings

logger = logging.getLogger(__name__)

KEYS_DIR = Path(__file__).resolve().parent.parent / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "receipt_private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "receipt_public.pem"

_cached_priv: bytes | None = None
_cached_pub: bytes | None = None
_cached_kid: str | None = None
_cached_source: str | None = None


def get_key_id(pub_pem: bytes) -> str:
    """Generate a short thumbprint prefix from public key SubjectPublicKeyInfo bytes."""
    return hashlib.sha256(pub_pem.strip()).hexdigest()[:16]


def has_explicit_private_key() -> bool:
    """Check if an explicit environment variable contains a private key PEM."""
    val = getattr(settings, "RECEIPT_PRIVATE_KEY_PEM", None) or os.environ.get(
        "RECEIPT_PRIVATE_KEY_PEM"
    )
    return bool(val and val.strip())


def validate_receipt_key_security(env: str | None = None) -> None:
    """Validate that production environments require an explicit stable signing key."""
    current_env = env or settings.FASTAPI_ENV
    if current_env == "production" and not has_explicit_private_key():
        raise RuntimeError(
            "Production startup aborted: RECEIPT_PRIVATE_KEY_PEM environment variable must be set in production"
        )


def _load_key_from_env() -> tuple[bytes, bytes, str] | None:
    raw_env = getattr(settings, "RECEIPT_PRIVATE_KEY_PEM", None) or os.environ.get(
        "RECEIPT_PRIVATE_KEY_PEM"
    )
    if not raw_env or not raw_env.strip():
        return None

    # Handle escaped newlines from environment variables
    pem_str = raw_env.strip().replace("\\n", "\n")
    pem_bytes = pem_str.encode("utf-8")
    try:
        priv_obj = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(priv_obj, rsa.RSAPrivateKey):
            raise ValueError("Configured private key is not an RSA private key")

        priv_pem = priv_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_pem = priv_obj.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        kid = get_key_id(pub_pem)
        logger.info(
            "[receipt_key] Signing key loaded from environment variable (source: env)"
        )
        return priv_pem, pub_pem, kid
    except Exception as exc:
        logger.error(
            "[receipt_key] Failed to load key from RECEIPT_PRIVATE_KEY_PEM: %s", exc
        )
        raise ValueError(f"Invalid RECEIPT_PRIVATE_KEY_PEM: {exc}") from exc


def get_receipt_keys(*, reload: bool = False) -> tuple[bytes, bytes, str]:
    """Resolve and return (private_pem, public_pem, key_id).

    Resolution priority:
      (a) Explicit environment variable RECEIPT_PRIVATE_KEY_PEM
      (b) Local disk file in keys/receipt_private.pem (if present in dev/demo)
      (c) Ephemeral in-memory generation with loud demo warning (aborts in production)
    """
    global _cached_priv, _cached_pub, _cached_kid, _cached_source

    if not reload and _cached_priv and _cached_pub and _cached_kid:
        return _cached_priv, _cached_pub, _cached_kid

    # (a) Environment variable
    env_keys = _load_key_from_env()
    if env_keys:
        _cached_priv, _cached_pub, _cached_kid = env_keys
        _cached_source = "env"
        return _cached_priv, _cached_pub, _cached_kid

    # Check production requirement
    if settings.FASTAPI_ENV == "production":
        raise RuntimeError(
            "Production startup aborted: RECEIPT_PRIVATE_KEY_PEM environment variable must be set in production"
        )

    # (b) Local disk file
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        priv_bytes = PRIVATE_KEY_PATH.read_bytes()
        pub_bytes = PUBLIC_KEY_PATH.read_bytes()
        kid = get_key_id(pub_bytes)
        logger.info("[receipt_key] Signing key loaded from disk file (source: file)")
        _cached_priv, _cached_pub, _cached_kid = priv_bytes, pub_bytes, kid
        _cached_source = "file"
        return _cached_priv, _cached_pub, _cached_kid

    # (c) Ephemeral fallback in demo/development
    logger.warning("****************************************************************")
    logger.warning(
        "[receipt_key] WARNING: No explicit RECEIPT_PRIVATE_KEY_PEM configured. "
        "Generating ephemeral RSA 2048-bit keypair (source: ephemeral). "
        "Receipts will not survive container redeployment."
    )
    logger.warning("****************************************************************")

    priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = get_key_id(pub_pem)

    try:
        PRIVATE_KEY_PATH.write_bytes(priv_pem)
        PUBLIC_KEY_PATH.write_bytes(pub_pem)
    except Exception as exc:
        logger.debug("[receipt_key] Could not persist key to disk: %s", exc)

    _cached_priv, _cached_pub, _cached_kid = priv_pem, pub_pem, kid
    _cached_source = "ephemeral"
    return _cached_priv, _cached_pub, _cached_kid


def ensure_receipt_keys() -> tuple[bytes, bytes]:
    """Backward-compatible helper returning (private_pem, public_pem)."""
    priv, pub, _ = get_receipt_keys()
    return priv, pub


def get_public_key_pem() -> bytes:
    """Return SubjectPublicKeyInfo PEM bytes for the active receipt signing key."""
    _, pub, _ = get_receipt_keys()
    return pub


def get_public_key_info() -> dict[str, str]:
    """Return public key metadata dictionary."""
    _, pub, kid = get_receipt_keys()
    return {
        "kid": kid,
        "algorithm": "RS256",
        "public_key": pub.decode("utf-8"),
    }


def sign_release_receipt(
    *,
    receipt_id: str | None = None,
    instrument_id: str,
    instrument_ref_no: str,
    path: str,
    release_id: str | None = None,
) -> str:
    """Sign an authorised release receipt using RS256.

    Payload contains strictly:
    - receipt_id
    - iat
    - instrument_hash (short SHA-256 of ref_no + id)
    - path
    - kid
    - release_id (optional)

    NO financial amounts and NO personal identifiers (satisfies Invariant I9).
    Token header contains:
    - kid: short public key thumbprint
    - alg: RS256
    """
    priv_pem, _, kid = get_receipt_keys()
    rid = receipt_id or str(uuid.uuid4())
    raw_hash = hashlib.sha256(
        f"{instrument_ref_no}:{instrument_id}".encode()
    ).hexdigest()[:16]

    payload: dict[str, Any] = {
        "receipt_id": rid,
        "iat": int(datetime.now(UTC).timestamp()),
        "instrument_hash": raw_hash,
        "path": path,
        "kid": kid,
    }
    if release_id:
        payload["release_id"] = str(release_id)

    token = jwt.encode(payload, priv_pem, algorithm="RS256", headers={"kid": kid})
    return token


def verify_release_receipt(
    token: str,
    public_key_pem: bytes | str | None = None,
    expected_kid: str | None = None,
) -> dict[str, Any]:
    """Cryptographically verify a release receipt token.

    Strictly pins algorithm to RS256 to reject 'none' or algorithm confusion attacks.
    Validates key id (kid) and returns decoded claims.
    """
    if not token or not isinstance(token, str):
        raise ValueError("malformed: empty or invalid token format")

    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise ValueError(f"malformed: invalid token header ({exc})") from exc

    alg = header.get("alg")
    if alg != "RS256":
        raise ValueError(
            f"rejected algorithm: algorithm '{alg}' is not permitted; pinned to RS256"
        )

    token_kid = header.get("kid")
    pub_bytes = public_key_pem
    active_kid = expected_kid

    if pub_bytes is None:
        _, def_pub, def_kid = get_receipt_keys()
        pub_bytes = def_pub
        if active_kid is None:
            active_kid = def_kid

    if isinstance(pub_bytes, str):
        pub_bytes = pub_bytes.encode("utf-8")

    if token_kid and active_kid and token_kid != active_kid:
        raise ValueError(
            f"unknown key: key id '{token_kid}' does not match expected '{active_kid}'"
        )

    try:
        decoded: dict[str, Any] = jwt.decode(
            token,
            pub_bytes,
            algorithms=["RS256"],
            options={"require": ["receipt_id", "iat", "instrument_hash", "path"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("expired: receipt token has expired") from exc
    except jwt.InvalidSignatureError as exc:
        raise ValueError("bad signature: cryptographic verification failed") from exc
    except jwt.DecodeError as exc:
        raise ValueError("malformed: token payload decode failed") from exc
    except Exception as exc:
        raise ValueError(f"malformed: {exc}") from exc

    return decoded
