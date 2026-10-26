import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


def test_webhook_signature_accepts_current_body_and_rejects_replay() -> None:
    from app.integration.webhooks import sign_webhook, verify_webhook

    body = b'{"event":"deposit.confirmed"}'
    headers = sign_webhook(body, {"v1": b"test-webhook-secret"})
    assert verify_webhook(body, headers, {"v1": b"test-webhook-secret"})

    with pytest.raises(ValueError, match="replay"):
        verify_webhook(
            body,
            sign_webhook(
                body,
                {"v1": b"test-webhook-secret"},
                timestamp=int((datetime.now(UTC) - timedelta(minutes=6)).timestamp()),
            ),
            {"v1": b"test-webhook-secret"},
        )


def test_webhook_key_rotation_and_tamper_are_checked() -> None:
    from app.integration.webhooks import sign_webhook, verify_webhook

    body = b"payload"
    headers = sign_webhook(body, {"v2": b"new-secret"}, key_id="v2")
    assert verify_webhook(body, headers, {"v1": b"old-secret", "v2": b"new-secret"})
    with pytest.raises(ValueError, match="signature"):
        verify_webhook(b"changed", headers, {"v2": b"new-secret"})


def test_api_key_is_hash_only_and_scope_checked() -> None:
    from app.integration.apikeys import hash_api_key, issue_api_key, verify_api_key

    raw, record = issue_api_key("aicte-sandbox", {"coverage:read"})
    assert raw.startswith("fdr_")
    assert record.key_hash == hash_api_key(raw)
    assert raw not in record.key_hash
    assert verify_api_key(raw, record, "coverage:read")
    assert not verify_api_key(raw, record, "institutions:write")
    assert not verify_api_key(raw + "x", record, "coverage:read")


def test_idempotency_rejects_same_key_for_different_body() -> None:
    from app.integration.idempotency import body_hash, ensure_same_request

    first = body_hash({"permanent_id": "P-1", "name": "Synthetic"})
    assert ensure_same_request(first, first)
    with pytest.raises(ValueError, match="different request"):
        ensure_same_request(first, body_hash({"permanent_id": "P-1", "name": "Changed"}))


def test_checkpoint_is_signed_and_stored_outside_database(tmp_path: Path) -> None:
    from app.integration.checkpoints import AuditCheckpointSigner

    signer = AuditCheckpointSigner.generate(tmp_path)
    record = signer.write(up_to_id=12, head_hash="a" * 64)
    assert (tmp_path / "checkpoint-12.json").exists()
    assert signer.verify(record)
    altered = json.loads(json.dumps(record))
    altered["head_hash"] = "b" * 64
    assert not signer.verify(altered)


def test_programme_screen_contract_is_rule_backed() -> None:
    from app.domain.rules import load_rule

    rules = load_rule(Path("app/rules"), "deposit", datetime.now(UTC).date())
    rule_programmes = set(rules["programme_amounts_paise"])
    assert rule_programmes == {
        "Engineering and Technology",
        "Planning",
        "Applied Arts and Crafts",
        "Design",
        "Hotel Management and Catering Technology",
        "Computer Applications",
        "Management",
    }
    screen = Path(__file__).parents[2] / "frontend/src/routes/_layout/deposits.tsx"
    source = screen.read_text(encoding="utf-8")
    assert "programmesData?.programmes?.map" in source
    assert "Pharmacy" not in source


def test_machine_api_bulk_upsert_and_coverage_are_scoped(
    client, db
) -> None:
    from app.integration.apikeys import issue_api_key

    raw, record = issue_api_key(
        "synthetic-aicte", {"institutions:write", "coverage:read"}
    )
    db.add(record)
    db.commit()
    permanent_id = f"P-INTEGRATION-{uuid.uuid4().hex[:8]}"
    payload = {
        "permanent_id": permanent_id,
        "name": "Synthetic Integration Institution",
        "region": "NR",
        "programmes": [{"category": "Computer Applications", "level": "UG"}],
    }
    headers = {
        "X-API-Key": raw,
        "Idempotency-Key": f"bulk-{uuid.uuid4().hex}",
    }
    first = client.post(
        "/api/v1/integration/institutions:bulk-upsert?dry_run=false",
        json=[payload],
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["created"] == 1
    replay = client.post(
        "/api/v1/integration/institutions:bulk-upsert?dry_run=false",
        json=[payload],
        headers=headers,
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()
    mismatch = client.post(
        "/api/v1/integration/institutions:bulk-upsert?dry_run=false",
        json=[{**payload, "name": "Different body"}],
        headers=headers,
    )
    assert mismatch.status_code == 422
    coverage = client.get(
        f"/api/v1/integration/institutions/{permanent_id}/coverage-status",
        headers={"X-API-Key": raw},
    )
    assert coverage.status_code == 200
    assert coverage.json()["rule_status"] == "DEMO"


def test_machine_api_scope_and_signature_errors_are_explicit(client, db) -> None:
    from app.integration.apikeys import issue_api_key

    raw, record = issue_api_key("read-only", {"coverage:read"})
    db.add(record)
    db.commit()
    response = client.post(
        "/api/v1/integration/institutions:bulk-upsert",
        json=[],
        headers={"X-API-Key": raw},
    )
    assert response.status_code == 403


def test_outbox_dispatch_is_idempotent_and_dead_letters_after_retries(db) -> None:
    from app.integration.outbox import dispatch_once, enqueue
    from app.models import OutboxMessage
    from sqlmodel import delete, select

    db.exec(delete(OutboxMessage))
    db.commit()
    delivered: list[str] = []
    first = enqueue(
        db,
        event_type="deposit.confirmed",
        aggregate_type="instrument",
        aggregate_id="synthetic-1",
        payload={"state": "confirmed"},
    )
    db.commit()
    assert dispatch_once(db, lambda message: delivered.append(str(message.id)), batch_size=1) == 1
    assert delivered == [str(first.id)]
    assert dispatch_once(db, lambda _message: delivered.append("duplicate")) == 0

    failed = enqueue(
        db,
        event_type="deposit.overdue",
        aggregate_type="instrument",
        aggregate_id="synthetic-2",
        payload={"state": "overdue"},
    )
    db.commit()
    assert dispatch_once(db, lambda _message: (_ for _ in ()).throw(RuntimeError("down")), max_attempts=1) == 0
    stored = db.exec(select(OutboxMessage).where(OutboxMessage.id == failed.id)).one()
    assert stored.dead_lettered_at is not None
