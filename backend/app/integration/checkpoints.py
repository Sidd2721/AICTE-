"""Signed audit checkpoints written to a filesystem outside PostgreSQL."""

import base64
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlmodel import Session, col, select

from app.models import AuditEvent


class AuditCheckpointSigner:
    def __init__(self, directory: Path, private_key: Ed25519PrivateKey) -> None:
        self.directory = directory
        self.private_key = private_key

    @classmethod
    def generate(cls, directory: Path) -> AuditCheckpointSigner:
        return cls(directory, Ed25519PrivateKey.generate())

    @classmethod
    def from_private_key_file(
        cls, directory: Path, key_path: Path
    ) -> AuditCheckpointSigner:
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("checkpoint key must be Ed25519")
        return cls(directory, key)

    def public_key_pem(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def _signed_bytes(self, record: dict[str, Any]) -> bytes:
        unsigned = {k: record[k] for k in ("up_to_id", "head_hash", "created_at")}
        return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()

    def write(self, *, up_to_id: int, head_hash: str) -> dict[str, Any]:
        if len(head_hash) != 64 or any(c not in "0123456789abcdef" for c in head_hash):
            raise ValueError("head_hash must be a lowercase SHA-256 hex digest")
        record: dict[str, Any] = {
            "up_to_id": up_to_id,
            "head_hash": head_hash,
            "created_at": datetime.now(UTC).isoformat(),
        }
        record["signature"] = base64.b64encode(
            self.private_key.sign(self._signed_bytes(record))
        ).decode("ascii")
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self.directory / f"checkpoint-{up_to_id}.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(record, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, destination)
        return record

    def verify(self, record: dict[str, Any]) -> bool:
        try:
            signature = base64.b64decode(record["signature"], validate=True)
            public_key = self.private_key.public_key()
            public_key.verify(signature, self._signed_bytes(record))
            return True
        except InvalidSignature, KeyError, ValueError, TypeError:
            return False


def write_latest_audit_checkpoint(
    session: Session, signer: AuditCheckpointSigner
) -> dict[str, Any] | None:
    latest = session.exec(
        select(AuditEvent).order_by(col(AuditEvent.id).desc())
    ).first()
    if latest is None or latest.id is None:
        return None
    return signer.write(up_to_id=int(latest.id), head_hash=latest.hash)
