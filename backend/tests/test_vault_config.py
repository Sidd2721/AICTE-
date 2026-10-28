from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from app.core.config import settings
from app.domain.vault import (
    check_vault_writable,
    decrypt_bytes,
    encrypt_bytes,
    get_vault_dir,
    validate_vault_security,
)


def test_vault_dir_default_and_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test default vault directory and custom VAULT_PATH override."""
    monkeypatch.setattr(settings, "VAULT_PATH", None)
    default_dir = get_vault_dir()
    assert default_dir.name == "vault"

    custom_dir = tmp_path / "custom_vault"
    monkeypatch.setattr(settings, "VAULT_PATH", str(custom_dir))
    assert get_vault_dir() == custom_dir.resolve()


def test_check_vault_writable(tmp_path: Path):
    """Verify write probe works on existing or newly created directories."""
    valid_dir = tmp_path / "sub_vault"
    assert check_vault_writable(valid_dir) is True
    assert valid_dir.exists()


def test_validate_vault_security_production_refusal(monkeypatch: pytest.MonkeyPatch):
    """Production must refuse to start if VAULT_KEY is empty or matches SECRET_KEY."""
    monkeypatch.setattr(settings, "VAULT_KEY", "")
    with pytest.raises(RuntimeError, match="Production startup aborted"):
        validate_vault_security(env="production")

    monkeypatch.setattr(settings, "SECRET_KEY", "same-secret-key-for-both-32chars-min")
    monkeypatch.setattr(settings, "VAULT_KEY", "same-secret-key-for-both-32chars-min")
    with pytest.raises(RuntimeError, match="Production startup aborted"):
        validate_vault_security(env="production")

    monkeypatch.setattr(settings, "VAULT_KEY", "")
    validate_vault_security(env="demo")


def test_vault_key_immutability_document_loss(monkeypatch: pytest.MonkeyPatch):
    """Document that changing VAULT_KEY makes existing encrypted files unreadable."""
    key1 = "4GjN7xR8kL2mP9qT5vW3yA1cE6hJ8nM0oQ2sU4wX6zI="
    key2 = "9ZkP2xL1mQ5vW3yA1cE6hJ8nM0oQ2sU4wX6zI4GjN7x="

    monkeypatch.setattr(settings, "VAULT_KEY", key1)
    original_payload = b"CRITICAL_REGULATORY_DEPOSIT_RECEIPT_PDF"
    encrypted = encrypt_bytes(original_payload)

    decrypted = decrypt_bytes(encrypted)
    assert decrypted == original_payload

    monkeypatch.setattr(settings, "VAULT_KEY", key2)
    with pytest.raises(InvalidTag):
        decrypt_bytes(encrypted)
