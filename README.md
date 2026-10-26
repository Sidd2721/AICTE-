# AICTE Security Deposit / Fixed Deposit Receipt (FDR) Portal
**SIH Problem Statement PS 26265** — High-Assurance Regulatory Deposit Management System.  
Automates institutional security deposit submissions, independent cryptographic bank confirmations, automated renewal/expiry monitoring, and strict dual-custody release authorization for AICTE.  
Engineered with defense-in-depth: Python 3.14, PostgreSQL Row-Level Security (`NOSUPERUSER`), SHA-256 hash-chained audit ledger, integer-paise accounting, and cryptographic bank confirmation gates.

---

## Live Demo Guide
See [DEMO.md](DEMO.md) for the complete 7-step evaluation walkthrough matching `run-demo.ps1`.

---

## 3 Commands to Run

```powershell
# 1. System Doctor (preflight environment & prerequisite validation)
python scripts/doctor.py

# 2. One-Command Showcase Demo (clean DB reset, seed, and 7-step automated verification)
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset

# 3. Quality Gate (137 tests, mypy, ruff, biome, prod build, leak check, capability map, openapi drift)
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

---

## Limits of This Prototype
- **DEMO Rule Values**: Rule values are marked `DEMO` pending official handbook confirmation; startup is blocked in production.
- **SIMULATED Bank & Email**: Bank and email interactions are SIMULATED and transparently labelled.
- **DSC Unsigned**: DSC receipts are unsigned test certificates, not bank confirmations.
- **Synthetic Data & Metrics**: All institutions, deposit amounts, reference numbers, and metrics are synthetic.
- **No Real Integration**: No live banking networks (SFMS/CBS) or external ERP connections.
- **Single-Process Rate Limiter**: Rate limiting is designed for single-node / demonstration environments.

---

## Intentionally Deferred Features
1. **Triage bins**
2. **Wizard rewrite** (server-side draft, idempotency)
3. **Dedicated metrics endpoint**
4. **Fully responsive mobile layout**
5. **Interactive onboarding tour**
6. **Hindi (bilingual localization)**
7. **Dark mode**
8. **Notification bell UI**
9. **PDF report generation** (CSV with formula-sanitization supported)

---

## Seed Matrix & Test Credentials

The portal is seeded with a dual-region, dual-custody maker-checker matrix (`backend/app/core/db.py`):

| Role | Email | Region / Scope | Responsibilities |
|---|---|---|---|
| **Institution** | `inst.north1@example.com` | North Region | Submits FDR details, views Table 1.4 coverage card, renews deposits. |
| **Regional Officer (Maker)** | `officer.north@example.com` | North Region | Scrutinizes submissions, verifies release requests (cannot approve). |
| **Regional Checker** | `checker.north@example.com` | North Region | Verifies officer recommendations (maker-checker separation). |
| **Bureau Approver (Checker)** | `bureau@example.com` | National | Advances system clock, approves verified release requests. |
| **Auditor** | `auditor@example.com` | National | Read-only oversight across all regions; verifies SHA-256 audit ledger. |
| **System Admin** | `admin@example.com` | System | System administration, rulebook inspection, and user provisioning. |

*Default password for all demo accounts: `changethis` (tree-shaken out of production builds).*

---

## Architecture & Hard Invariants (I1–I15)

- **I1: Python 3.14**: Uses native `except A, B:` syntax.
- **I2: Runtime RLS**: Role `app` has `NOSUPERUSER` and `NOBYPASSRLS`. Missing RLS context returns 0 rows.
- **I3: Bank Gate**: Requires valid signature, non-repudiation key usage, matching pinned authority, and exact byte-prefix matching.
- **I4: Audit Ledger**: Append-only via `audit_append()`; verified by hash-chain traversal (`audit_verify()`).
- **I5: Integer Money**: All amounts in paise (`bigint`). Zero floats.
- **I6: Maker-Checker**: `verified_by <> approved_by` strictly enforced on release and scrutiny workflows.
- **I7: Dated Rules**: All deposit requirements are loaded from versioned JSON rulebooks; DEMO files block startup in production.
- **I8: Dynamic Next Action**: Primary workflow buttons are served by `next_action()` backend logic.
- **I9: Privacy & Secrets**: No real FDR numbers, PII, or secrets in git, logs, or test fixtures.
- **I10: File Validation**: Magic bytes validation prevents disguised file uploads.
- **I11: Token Lifetime**: Access tokens expire in 60 minutes.
- **I12: Dynamic Trust**: Computed dynamically (`claimed`, `confirmed`, `stale`, `changed`).
- **I13: Distributed Rate Limiting**: Shared Postgres-backed rate limiting.
- **I14: CSV Sanitization**: Formula injection neutralized via `csv_safe`.
- **I15: Vault Encryption**: AES-256-GCM authenticated encryption with record-bound AAD.

---

## License & Evaluation Notice
Prototype developed for AICTE Problem Statement PS 26265. All rights reserved.
