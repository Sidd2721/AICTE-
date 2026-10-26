# AICTE Security Deposit / Fixed Deposit Receipt (FDR) Portal
**SIH Problem Statement PS 26265** — High-Assurance Regulatory Deposit Management System.  
Automates institutional security deposit submissions, independent cryptographic bank confirmations, automated renewal/expiry monitoring, and strict dual-custody release authorization for AICTE.  
Engineered with defense-in-depth: Python 3.14, PostgreSQL Row-Level Security (`NOSUPERUSER`), SHA-256 hash-chained audit ledger, integer-paise accounting, and cryptographic bank confirmation gates.

---

## 3 Commands to Run

```powershell
# 1. System Doctor (preflight environment & prerequisite validation)
python scripts/doctor.py

# 2. One-Command Showcase Demo (clean DB reset, seed, and 7-step automated verification)
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset

# 3. Quality Gate (136 tests, mypy, ruff, biome, prod build, leak check, capability map, openapi drift)
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
```

---

## Prototype Boundaries & What It Does NOT Do
- **Synthetic Data Only:** All institutions, deposit amounts, reference numbers, and user profiles are synthetic.
- **Labelled Bank Simulators:** Real banking networks (SFMS/CBS) do not expose public sandboxes for hackathons; all bank confirmation flows operate through transparently labelled, cryptographically rigorous simulators.
- **No Real Money Movement:** The portal orchestrates regulatory custody and legal release authorizations; funds remain in designated commercial banks under joint lien.
- **Demo Mode Safeguards:** Rule configurations are marked `DEMO` and strictly block startup outside local development environments.

---

## Intentionally Deferred Features (To Keep Assurance High)
1. **Live SFMS / ISO 20022 Banking Gateway:** Replaced with cryptographic PyHanko signed letter verification gate (testing byte-tampering, invalid chains, and token replays).
2. **Hardware USB Token PKCS#11 Integration:** Digital signatures simulated with X.509 CMS certificates; unverified documents clearly tagged *"unsigned, not a bank confirmation"*.
3. **External Telecom SMS Gateway:** Replaced with transactional in-database notice queue and email dispatch logs.
4. **Third-Party University Affiliation ERP Sync:** Institutional programme quotas and Table 1.4 thresholds are evaluated via deterministic regulatory rulebooks.
5. **Real-Money Payment Gateway:** AICTE security deposits are fixed deposits pledged under joint lien, not cash payments into an AICTE clearing account.

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
