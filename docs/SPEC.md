# Specification — AICTE Security Deposit / FDR Portal (PS 26265)

## 1. Problem Statement & Mission
AICTE Problem Statement PS 26265: Every security deposit or FDR held by AICTE has one record, an owner, a next action, and a deadline, and every fact is marked CLAIMED or BANK-CONFIRMED with method and date.

This is a prototype for a government regulator using synthetic data. All banking and external regulator integrations are labelled simulators. Real money is never moved.

## 2. Invariants (Hard Constraints)
- **I1 (Computed Trust Badge):** The trust badge is computed dynamically (`claimed`, `confirmed`, `stale`, `changed`), never stored as a state in the database.
- **I2 (Degradation Mode):** Bank source unreachable or down produces status `"unavailable"` ("source unavailable"), never `"mismatch"`.
- **I3 (Strict Cryptographic Bank Gate):** Bank confirmation accepted only via the full gate: exact letter prefix match, single valid signature, trusted cert, full file coverage, matching pinned bank SHA-256 fingerprint, and non-repudiation key usage.
- **I4 (Least Privilege Database Access):** Runtime database connection connects as `NOSUPERUSER`, `NOBYPASSRLS`. `set_rls_context()` must be invoked immediately upon authentication. Unauthenticated requests see 0 tenant rows.
- **I5 (Tamper-Evident Audit Ledger):** Audit events are append-only into a SHA-256 hash-chained ledger via `audit_append()` (SECURITY DEFINER with advisory lock). Payloads reject floats, NaNs, and non-string keys.
- **I6 (Integer Money in Paise):** All financial values are stored as integer paise (`bigint`). 1 lakh = 10,000,000 paise. Floats are strictly prohibited. Timestamps stored in UTC, formatted in IST.
- **I7 (Dated Rulebook):** Regulatory rules are dated JSON files. Startup refuses non-CONFIRMED rules in production mode.
- **I8 (Dual Custody / Maker-Checker):** The user who verifies a release request cannot approve it (`verified_by <> approved_by`). The system recommends; humans release.
- **I9 (Zero Leakage):** No real secrets, FDR numbers, or personal data in git, code, tests, or logs. `.env` is never tracked.
- **I10 (Uniform Endpoint Security):** Every endpoint requires authentication, tenant RLS isolation, and structured audit events for state mutations. Cross-scope operations return 403 Forbidden.
- **I11 (Invite-Only Access):** No public signup. 60-minute token expiration. Auth endpoints are rate-limited.
- **I12 (Official Regulatory Grounding):** Deposit figures originate solely from Approval Process Handbook Table 1.4.
- **I13 (DSC Verification):** A Digital Signature Certificate on an uploaded document proves identity of the submitter, not bank confirmation.
- **I14 (UI Action Determinism):** Primary call-to-action buttons derive entirely from `next_action()`. No action state machines in frontend client code.
- **I15 (Isolated Simulators):** Simulators operate exclusively under `/sim` or development adapters, only when `FASTAPI_ENV == "development"` or `"demo"`, with prominent "SIMULATED" watermarks.

## 3. Database Roles & Isolation
- `migrator`: Database owner role used solely for DDL migrations via Alembic (`MIGRATION_DATABASE_URL`).
- `app`: Runtime application role with `NOSUPERUSER` and `NOBYPASSRLS` privileges (`DATABASE_URL`).
- Application tenant roles: `institution`, `regional` (maker), `bureau` (checker & admin), `auditor` (read-only).
