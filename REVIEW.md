# REVIEW — Project Architecture & Deployment Readiness Assessment

**Mandate:** AICTE PS 26265 (Monitoring & Verification of Fixed Deposit Receipts)  
**Verification Status:** All P0 and P1 items resolved in repository codebase.

---

## 1. Verdict

The project matches the problem statement goals: server-driven UI, least-privilege database role with row-level security (`NOSUPERUSER NOBYPASSRLS`), dual-control release enforced by database constraints and service layer, tamper-evident SHA-256 audit ledger, dated rules engine, and cryptographic 6-point bank confirmation gate.

---

## 2. Findings & Resolution Status

### P0-1. Bank Gate Binding to Issued Letter
- **Finding:** A generic bank signature check might accept a different letter signed by the same trusted bank key if not cryptographically bound.
- **Resolution:** `backend/app/domain/bank_gate.py` explicitly enforces `reply.startswith(issued)` as Check 1 before any ASN.1 parsing. If a different letter is signed by the trusted key, the gate rejects it immediately with reason `not_our_letter`.
- **Proving Test:** `backend/tests/test_bank_gate.py::test_3_other_document_signed_by_trusted_key_rejected` verifies this exact attack vector and passes.

### P0-2. Repository Hygiene & Personal Path Leaks
- **Finding:** Absolute file links, Windows local paths, or agent folders must not be committed to GitHub.
- **Resolution:**
  - Removed all absolute file URLs from `docs/LIMITS.md` and `.gemini/GEMINI.md`.
  - Updated `scripts/doc_refs.py` to automatically scan and fail if any absolute file URL is introduced into documentation.
  - Added `secrets-scan` job to `.github/workflows/ci.yml`.

### P0-3. Vault Storage on Ephemeral Disk
- **Finding:** Render free instances have an ephemeral filesystem; stored PDF uploads reset on cold-wake.
- **Resolution:**
  - Explicitly documented in `DEPLOY-GUIDE.md` and `README.md`.
  - For demo evaluation, rich synthetic seed data is automatically initialized on boot via `app/initial_data.py`.
  - For production cloud rollout, the vault adapter supports cloud object storage (S3 / MeghRaj) with server-side KMS encryption.

### P0-4. Demo Login & Docs Exposure on Public URLs
- **Finding:** Demo login personas and Swagger `/docs` should not be publicly accessible in strict production mode.
- **Resolution:**
  - `FASTAPI_ENV` is strictly validated (`development`, `demo`, `production`).
  - When `FASTAPI_ENV == "production"`, Swagger `/docs` returns 404, simulators under `/sim` are disabled, and demo persona logins are blocked.

### P0-5. Test Suite Remote Database Protection
- **Finding:** Running `pytest` when `DATABASE_URL` accidentally points to a live or managed database (like Neon) would truncate tables during teardown.
- **Resolution:**
  - Created `backend/tests/conftest_guard_snippet.py` and placed it at the very top of `backend/tests/conftest.py`.
  - Tests verify that `DATABASE_URL` host is strictly local (`localhost`, `127.0.0.1`, `::1`, `db`, `postgres`). If pointed at an external host (e.g. `*.neon.tech`), it aborts with exit code 3 before connecting.

---

## 3. Deployment Artifacts Added

1. `scripts/db-roles-managed.sql` — Plain SQL script to configure non-superuser, non-bypassrls `app` role on managed Postgres providers like Neon.
2. `scripts/print_env_contract.py` — AST-based zero-drift validator ensuring all environment variables are declared in `Settings`.
3. `backend/scripts/assert_least_privilege.py` — Pre-boot assertion script verifying runtime database connection cannot bypass RLS.
4. `backend/scripts/start.sh` — Production startup script binding to dynamic `$PORT` and running prestart migrations.
5. `render.yaml` — Infrastructure blueprint for Render free Docker web service.
6. `scripts/verify.sh` — Cross-platform Bash full gate verification twin of `verify.ps1`.
7. `.github/workflows/ci.yml` — Automated CI pipeline running secrets scanning, database role isolation, types, lint, and full test suite.
