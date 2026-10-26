# Integration guide — proposed contract

**Status:** design plus tested building blocks. The repository has no live AICTE,
bank, identity or messaging connection. Current adapters and data are labelled
simulators.

## Contract

- API version: `/api/v1`; JSON; UTC timestamps; money is integer paise.
- Machine clients use scoped API keys. The database stores only a SHA-256 hash;
  the plaintext is printed once by `cd backend && uv run python ../scripts/create_integration_key.py ...`.
- State-changing integration calls accept `Idempotency-Key`. Reusing a key with
  another request body is rejected. Completed responses can be replayed safely.
- List consumers should use keyset pagination (`after_id`) rather than offsets on
  large instrument lists.
- Webhooks use `X-FDR-Signature: <key-id>=<HMAC-SHA256>` and
  `X-FDR-Timestamp`. Receivers reject timestamps outside five minutes and support
  overlapping signing keys during rotation.
- State changes enqueue an outbox event in the same database transaction. A
  `SKIP LOCKED` dispatcher retries with exponential backoff and dead-letters
  after eight failures. Consumers must deduplicate by event id.
- External signed audit checkpoints are written to the configured filesystem,
  outside PostgreSQL. A privileged database operator can alter database state;
  checkpoint verification makes that limitation visible rather than claiming
  database immutability.

## Endpoints

### Bulk institution upsert

`POST /api/v1/integration/institutions:bulk-upsert?dry_run=true`

Required scope: `institutions:write`.

```json
[
  {
    "permanent_id": "P-SYNTHETIC-001",
    "name": "Synthetic Institution",
    "region": "NR",
    "is_government": false,
    "leased_private": false,
    "programmes": [{"category": "Computer Applications", "level": "UG"}]
  }
]
```

The response includes `accepted`, `created`, `updated`, and row-level `errors`.
Dry runs make no institution changes. Programme categories are validated against
the active dated rule file.

### Coverage status

`GET /api/v1/integration/institutions/{permanent_id}/coverage-status`

Required scope: `coverage:read`.

The response contains `required_paise`, `confirmed_paise`, `claimed_paise`,
`status`, `as_of`, `rule_edition`, and `rule_status`. Status is one of
`covered`, `short`, `unconfirmed`, or `exempt`. Consumers must not take a
regulatory action while `rule_status` is `DEMO`.

## Proposed ports

| Port | Current adapter | Replacement to agree |
|---|---|---|
| Institution directory | Synthetic bulk API | AICTE master-data pull or push |
| Bank confirmation | In-process simulator | Bank-hosted mTLS API or regulator-approved messaging |
| Notification | Local Mailpit | Government e-mail gateway |
| Identity | Local invite-only users | OIDC single sign-on mapped to role, region and institution |

No SFMS, NeSL, DigiLocker, Aadhaar, Kafka, or Extension-of-Approval hold is
implemented or committed by this prototype. Those are proposed integrations that
require technical, legal and operational agreements first.

## Bank onboarding checklist

For each participating bank, agree on the confirmation contact, certificate
fingerprint and renewal date, certificate exchange test, turnaround target,
error codes, outage semantics (`source unavailable`, never `mismatch`), and a
manual-review path for PDFs re-saved before signing.

## Acceptance tests

1. Verify signature test vectors, including tampering and a five-minute replay.
2. Reuse an idempotency key with the same and a different body.
3. Run a dry-run import containing one invalid programme category.
4. Dispatch an outbox message through a failing handler until it is dead-lettered.
5. Confirm that bank outage is reported as `source unavailable`.
6. Restore a same-version PostgreSQL dump into an empty database, run migrations,
   execute `SELECT audit_verify();`, verify the append-only trigger, and run one
   `audit_append()` call.
