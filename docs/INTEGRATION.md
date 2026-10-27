# AICTE FDR & Security Deposit Regulatory Portal — Integration Specification & Contract
## Machine-to-Machine Integration Guide (Namespace: `/api/integration/v1`)

> **Contract Version**: 1.0.0  
> **Evolution Policy**: Additive-only (fields are never removed or renamed; clients must ignore unrecognized fields)  
> **Security Baseline**: Scoped API Keys (`X-API-Key`), Mutual TLS ready, Zero Superuser Privileges, RFC 7807/Standard Error Envelopes

---

## 1. Global Integration Architecture & Standards

All machine-to-machine integrations with the AICTE Security Deposit Portal are exposed under the namespace:
```
/api/integration/v1
```

### 1.1 Authentication & Scopes
Every integration request must include the API key header:
```http
X-API-Key: fdr_<key_id>_<secret>
```
API keys are issued and revoked exclusively by an authorized AICTE Bureau Officer. Only a SHA-256 digest of the key is stored in the database.

| Scope | Granted Capabilities | Target Integrator |
| :--- | :--- | :--- |
| `bank:confirm` | Submit digital confirmations, poll pending verification requests, access sandbox signers. | Scheduled Commercial Banks (Core Banking Systems / SFMS Adapters) |
| `aicte:read` | Read-only access to institutions, instruments, coverage status, and outbox event streams. | AICTE Approval Portal, National Data Services, CAG Audit Extractors |
| `aicte:webhooks` | Register, view, and revoke webhook subscriptions for real-time lifecycle event dispatch. | Automated Regulatory Workflow Engines |

### 1.2 Unified Error Envelope
All error responses (HTTP 4xx and 5xx) strictly return the following JSON envelope:
```json
{
  "code": "INVALID_SIGNATURE",
  "message": "The digital signature on the bank letter is invalid or untrusted.",
  "details": {
    "reason": "signer_not_pinned",
    "received_signer": "CN=Untrusted Root CA"
  },
  "request_id": "req_01928a3f89b"
}
```

### 1.3 Pagination Standard
All list endpoints utilize deterministic cursor pagination:
```json
{
  "items": [ ... ],
  "next_cursor": "eyJpZCI6ICJmZHI..."
}
```
If `next_cursor` is `null`, the final page of records has been reached.

### 1.4 Rate Limiting & Body Limits
- **Rate Limit Headers**: Every HTTP response includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`.
- **Throttling (HTTP 429)**: Returns `{ "code": "RATE_LIMIT_EXCEEDED", ... }` with a mandatory `Retry-After: <seconds>` header.
- **Maximum Request Body**: 10 MB. Exceeding requests return HTTP 413 Payload Too Large.

### 1.5 Accounting & Timestamps
- **Money**: Integer paise (`amount_paise`). 1 INR = 100 paise; ₹ 35 Lakh = `350000000`. Floating-point amounts are rejected.
- **Timestamps**: UTC ISO-8601 strings (e.g., `2026-10-27T10:30:00Z`).

---

## 2. Bank IT Integration (Bank Systems & CBS Gateways)

This section defines the API endpoints used by Core Banking Systems (CBS) and financial messaging adapters.

### Operation 2.1: Poll Pending Bank Verification Requests
Banks query outstanding confirmation inquiries awaiting verification for their institution branches.

- **Method**: `GET /api/integration/v1/bank/requests/pending`
- **Required Scope**: `bank:confirm`
- **Query Parameters**:
  - `ifsc` *(optional, string)*: Filter by branch IFSC code (e.g. `SBIN0001234`).
  - `limit` *(optional, int)*: Page size (default: 20, max: 100).
  - `cursor` *(optional, string)*: Pagination cursor.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/api/integration/v1/bank/requests/pending?ifsc=SBIN0001234&limit=10" \
     -H "X-API-Key: fdr_testkey_bankconfirmsecret123"
```

#### Example Response (HTTP 200):
```json
{
  "items": [
    {
      "request_token": "tok_sec_9812739182379",
      "instrument_id": "00000000-0000-0000-0001-000000000001",
      "ref_no": "FDR-B9-301",
      "bank_code": "SBIN",
      "ifsc": "SBIN0001234",
      "amount_paise": 350000000,
      "issue_date": "2024-01-15",
      "maturity_date": "2034-01-15",
      "expires_at": "2026-11-10T10:00:00Z"
    }
  ],
  "next_cursor": null
}
```

---

### Operation 2.2: Submit Authoritative Bank Confirmation
Banks submit cryptographically signed confirmation letters validating or rejecting a pledged deposit.

- **Method**: `POST /api/integration/v1/bank/confirmations`
- **Required Scope**: `bank:confirm`
- **Required Headers**:
  - `Idempotency-Key: <unique_uuid>`
  - `X-API-Key: <api_key>`
- **Request Body**:
  - `request_token` *(string, required)*: Single-use challenge token issued in the inquiry.
  - `signed_letter_base64` *(string, required)*: Base64-encoded PDF verification reply.
  - `fields` *(object, required)*:
    - `ref_no` *(string)*: Confirmed deposit number.
    - `bank_code` *(string)*: Pinned bank code.
    - `amount_paise` *(integer)*: Verified principal in integer paise.
    - `maturity_date` *(string, YYYY-MM-DD)*: Confirmed maturity date.
    - `lien_marked` *(boolean)*: Confirmation that joint lien in favor of AICTE is active in CBS.

#### Example Request:
```bash
curl -X POST "http://localhost:8000/api/integration/v1/bank/confirmations" \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: 7b247f52-78a0-4c3e-86d9-69317b6a1e01" \
     -H "X-API-Key: fdr_testkey_bankconfirmsecret123" \
     -d '{
       "request_token": "tok_sec_9812739182379",
       "signed_letter_base64": "JVBERi0xLjQgYXV0aGVudGljIGlzc3VlZCBpbnF1aXJ5IHJlcGx5...",
       "fields": {
         "ref_no": "FDR-B9-301",
         "bank_code": "SBIN",
         "amount_paise": 350000000,
         "maturity_date": "2034-01-15",
         "lien_marked": true
       }
     }'
```

#### Example Response (HTTP 200 - Accepted):
```json
{
  "verdict": "accepted",
  "instrument_id": "00000000-0000-0000-0001-000000000001",
  "instrument_status": "active",
  "badge": "confirmed",
  "discrepancy_count": 0,
  "checks": [
    {"name": "byte_prefix", "passed": true, "detail": "Valid PDF byte header matching issued document"},
    {"name": "entire_file_coverage", "passed": true, "detail": "Zero trailing appended bytes"},
    {"name": "trusted_root", "passed": true, "detail": "Valid CCA accredited Root CA anchor"},
    {"name": "non_repudiation", "passed": true, "detail": "Key usage nonRepudiation present"},
    {"name": "pinned_signer", "passed": true, "detail": "Matched pinned certificate serial for SBIN"}
  ]
}
```

#### Idempotency & Replay Semantics:
1. Re-submitting with the same `Idempotency-Key` and exact same body returns the cached HTTP 200 response.
2. Re-submitting with the same `Idempotency-Key` but modified payload returns **HTTP 422 Unprocessable Entity**.
3. Attempting to consume an already burned `request_token` with a new idempotency key returns **HTTP 409 Conflict** (`TOKEN_ALREADY_USED`).

---

### Operation 2.3: Bank Sandbox Signer (Development / Demo Only)
Generates an authentic mock signed letter for testing against the cryptographic gate.

- **Method**: `POST /api/integration/v1/sandbox/bank/sign`
- **Required Scope**: `bank:confirm`
- **Labels**: `SIMULATED` (refuses outside development/demo environments)

#### Example Request:
```bash
curl -X POST "http://localhost:8000/api/integration/v1/sandbox/bank/sign" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: fdr_testkey_bankconfirmsecret123" \
     -d '{
       "ref_no": "FDR-B9-301",
       "amount_paise": 350000000,
       "maturity_date": "2034-01-15",
       "lien_marked": true
     }'
```

---

## 3. AICTE IT Integration (Central Regulatory Data & Webhooks)

This section defines the API endpoints used by AICTE central IT systems, Ministry of Education dashboards, and event subscribers.

### Operation 3.1: Query Institutions
- **Method**: `GET /api/integration/v1/institutions`
- **Required Scope**: `aicte:read`
- **Query Parameters**:
  - `region` *(optional, string)*: Filter by region code (`NR`, `WR`, `SR`, `ER`).
  - `limit` *(optional, int)*: Maximum items to return (default: 50, max: 200).
  - `cursor` *(optional, string)*: Cursor for pagination.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/api/integration/v1/institutions?region=NR&limit=5" \
     -H "X-API-Key: fdr_testkey_aictereadsecret456"
```

---

### Operation 3.2: Query Instruments
- **Method**: `GET /api/integration/v1/instruments`
- **Required Scope**: `aicte:read`
- **Query Parameters**:
  - `lifecycle` *(optional, string)*: Filter by `pending`, `active`, `matured`, `renewed`, `released`.
  - `badge` *(optional, string)*: Filter by `claimed`, `confirmed`, `stale`, `changed`.
  - `updated_since` *(optional, string, ISO-8601)*: Return only records modified after this timestamp.
  - `limit` *(optional, int)*: Page size (default: 50, max: 200).
  - `cursor` *(optional, string)*: Cursor for pagination.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/api/integration/v1/instruments?lifecycle=active&badge=confirmed&limit=10" \
     -H "X-API-Key: fdr_testkey_aictereadsecret456"
```

#### Example Response:
```json
{
  "items": [
    {
      "id": "00000000-0000-0000-0001-000000000002",
      "institution_permanent_id": "P-DELHI-ENG-01",
      "ref_no": "FDR-B9-302",
      "bank_code": "SBIN",
      "ifsc": "SBIN0001234",
      "amount_paise": 350000000,
      "issue_date": "2024-01-15",
      "maturity_date": "2034-01-15",
      "kind": "FDR",
      "lifecycle": "active",
      "badge": "confirmed",
      "lien_marked": true,
      "updated_at": "2026-10-27T10:30:00Z"
    }
  ],
  "next_cursor": null
}
```

---

### Operation 3.3: Sequential Outbox Event Stream
Streams at-least-once lifecycle events recorded by the transactional outbox.

- **Method**: `GET /api/integration/v1/events`
- **Required Scope**: `aicte:read`
- **Query Parameters**:
  - `cursor` *(optional, string)*: Starting event sequence cursor.
  - `limit` *(optional, int)*: Maximum events to return (default: 100, max: 500).

#### Supported Schema-Versioned Event Types:
- `instrument.submitted` (Version 1.0)
- `instrument.confirmed` (Version 1.0)
- `instrument.discrepancy_flagged` (Version 1.0)
- `instrument.expiring` (Version 1.0)
- `instrument.matured` (Version 1.0)
- `instrument.renewed` (Version 1.0)
- `release.requested` (Version 1.0)
- `release.verified` (Version 1.0)
- `release.approved` (Version 1.0)

#### Example Response:
```json
{
  "items": [
    {
      "event_id": "01928b9c-76e2-7634-8b1e-7231459a81c2",
      "event_type": "instrument.confirmed",
      "aggregate_type": "instrument",
      "aggregate_id": "00000000-0000-0000-0001-000000000002",
      "payload": {
        "ref_no": "FDR-B9-302",
        "amount_paise": 350000000,
        "badge": "confirmed"
      },
      "created_at": "2026-10-27T10:30:00Z"
    }
  ],
  "next_cursor": "01928b9c-76e2-7634-8b1e-7231459a81c2"
}
```

---

### Operation 3.4: Webhook Subscriptions (SSRF-Protected)

Subscribes external endpoints to push events. Includes HMAC-SHA256 signature verification and automated SSRF address blocking.

- **Register Subscription**: `POST /api/integration/v1/webhooks`
- **List Subscriptions**: `GET /api/integration/v1/webhooks`
- **Delete Subscription**: `DELETE /api/integration/v1/webhooks/{id}`
- **Required Scope**: `aicte:webhooks`

#### SSRF Defense Rule:
The webhook dispatcher strictly validates target URLs. It forbids:
- IPv4 loopback (`127.0.0.0/8`, except in `development` environment for local testing)
- Private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
- Cloud instance metadata (`169.254.169.254`, `169.254.0.0/16`)
- Non-HTTP/HTTPS URI schemes.

#### Webhook Dispatch Headers:
```http
X-FDR-Signature: key1=9b3a9712f5a6b1284a7e8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e
X-FDR-Timestamp: 1793010600
```
**Verification formula**:
$$\text{Signature} = \text{HMAC-SHA256}(K_{\text{secret}}, \text{Timestamp} \parallel \text{"."} \parallel \text{RawBody})$$

---

## 4. API Key Lifecycle & Bureau Administration

Bureau Officers create, inspect, and revoke machine API keys via `/integrate` or `/api/v1/integration/keys`:
1. Keys are generated with 256 bits of cryptographically secure entropy (`secrets.token_urlsafe(32)`).
2. The raw secret is **shown exactly once** upon creation in the UI modal and is never stored or logged.
3. Every API call executes under an isolated, non-superuser RLS context with automatic audit logging:
   $$\text{Actor ID} = \text{API Key ID}$$
   $$\text{Action} = \text{"integration.request\_executed"}$$
