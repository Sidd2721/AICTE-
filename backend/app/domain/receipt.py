import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Keys storage location
KEYS_DIR = Path(__file__).parent.parent / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "receipt_private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "receipt_public.pem"


def ensure_receipt_keys() -> tuple[bytes, bytes]:
    """Ensure RSA 2048-bit keypair exists for receipt signing and offline verification."""
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if PRIVATE_KEY_PATH.exists() and PUBLIC_KEY_PATH.exists():
        return PRIVATE_KEY_PATH.read_bytes(), PUBLIC_KEY_PATH.read_bytes()

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    PRIVATE_KEY_PATH.write_bytes(private_pem)
    PUBLIC_KEY_PATH.write_bytes(public_pem)
    return private_pem, public_pem


def get_public_key_pem() -> bytes:
    _, pub = ensure_receipt_keys()
    return pub


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
    - release_id (optional)

    NO financial amounts and NO personal identifiers (satisfies Invariant I9).
    """
    priv_pem, _ = ensure_receipt_keys()
    rid = receipt_id or str(uuid.uuid4())
    raw_hash = hashlib.sha256(
        f"{instrument_ref_no}:{instrument_id}".encode()
    ).hexdigest()[:16]

    payload: dict[str, Any] = {
        "receipt_id": rid,
        "iat": int(datetime.now(UTC).timestamp()),
        "instrument_hash": raw_hash,
        "path": path,
    }
    if release_id:
        payload["release_id"] = str(release_id)

    token = jwt.encode(payload, priv_pem, algorithm="RS256")
    return token


def verify_release_receipt(
    token: str, public_key_pem: bytes | str | None = None
) -> dict[str, Any]:
    """Cryptographically verify a release receipt token.

    Strictly pins algorithm to RS256 to prevent 'none' or algorithm confusion attacks.
    """
    pub_key = public_key_pem or get_public_key_pem()
    if isinstance(pub_key, str):
        pub_key = pub_key.encode("utf-8")

    decoded: dict[str, Any] = jwt.decode(
        token,
        pub_key,
        algorithms=["RS256"],
        options={"require": ["receipt_id", "iat", "instrument_hash", "path"]},
    )
    return decoded
