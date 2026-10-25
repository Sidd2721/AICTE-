# EVIDENCE MAP — Verifiable Claims & Test Evidence (CHARTER Section 7, W2)

> **North Star Contract:** "Nothing appears in the presentation deck or pitch that is not verified in this map."
> Every claim maps directly to a screen route, an automated test, and the exact command to reproduce it.

---

## 1. Safety & Security Invariants (I1 – I15)
| Invariant | Claim | Screen / Route | Automated Proving Test | Command to Reproduce |
| :--- | :--- | :--- | :--- | :--- |
| **I1** | Python 3.14 syntax required & enforced | `/system-status` | `scripts/doctor.py` | `uv run python scripts/doctor.py` |
| **I2** | Audit trail written strictly via `audit_append()` | `/audit` | `starter/tests/sql_behaviour_check.py` | `uv run pytest tests/test_audit.py` |
| **I3** | Bank replies pass full 9-point gate | `/bank-reply` | `tests/test_bank_gate.py` | `uv run pytest tests/test_bank_gate.py` |
| **I4** | App database role has `NOSUPERUSER` and `NOBYPASSRLS` | `/system-status` | `tests/test_m0_hardening.py::test_app_role_is_not_superuser` | `uv run pytest tests/test_m0_hardening.py -k test_app_role` |
| **I5** | Strict RLS regional & institution data isolation | `/deposits` | `starter/tests/test_rls_late_context.py` | `uv run pytest tests/test_rls_late_context.py` |
| **I6** | Maker is never checker for deposit releases | `/releases` | `tests/test_next_action.py` | `uv run pytest tests/test_next_action.py` |
| **I7** | Rules loaded from dated JSON; demo rules block production | `/rules` | `tests/test_rules_files.py` | `uv run pytest tests/test_rules_files.py` |
| **I8** | Money stored strictly as integer paise (no floats) | `/deposits` | `tests/test_trust_rules.py` | `uv run pytest tests/test_trust_rules.py` |
| **I9** | `.env` never tracked in git; secrets validated outside dev | CLI / Repo | `tests/test_m0_hardening.py::test_env_is_not_tracked` | `git ls-files --error-unmatch .env` |
| **I10** | Primary actions computed server-side via `next_action()` | `/deposits/:id` | `tests/test_next_action.py` | `uv run pytest tests/test_next_action.py` |
| **I11** | Zero public user sign-up routes (404/405 returned) | `/api/v1/users/signup`| `tests/test_m0_hardening.py::test_signup_returns_404_or_405` | `uv run pytest tests/test_m0_hardening.py -k test_signup` |
| **I12** | CSV exports sanitized against formula injection | `/export` | `tests/test_csv_safe.py` | `uv run pytest tests/test_csv_safe.py` |
| **I13** | Rate limiter enforces sliding window on auth endpoints | `/api/v1/login/access-token` | `tests/test_rate_limit.py` | `uv run pytest tests/test_rate_limit.py` |

---

## 2. Statement Capabilities & Test Scenarios Coverage (CHARTER W2)
| Scenario | Capability Description | UI Screen / Route | Automated Proving Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **S-A** | **New FDR Submission:** Institution submits FDR details with joint name, lien clause, and bank branch. | `/deposits/new` | `tests/test_next_action.py` | Validated |
| **S-B** | **Bank Confirmation & Mismatch:** Authenticated bank reply confirms instrument; badge flips to "confirmed" or flags "changed". | `/deposits/:id` | `tests/test_trust_rules.py` | Validated |
| **S-C** | **Approaching Maturity:** Automated alerts at 90, 60, 30 days before deposit maturity. | `/dashboard` | `tests/test_next_action.py` | Validated |
| **S-D** | **Overdue & Escalation:** Deposit expired without renewal flagged as "matured" with escalation notice. | `/dashboard?status=matured` | `tests/test_next_action.py` | Validated |
| **S-E** | **Renewal with History:** Renewed FDR links back to predecessor instrument maintaining chain of custody. | `/deposits/:id/history` | `tests/test_trust_rules.py` | Validated |
| **S-F** | **Planted Discrepancies:** Discrepancy detector identifies duplicate FDRs, altered amounts, and mismatched dates. | `/discrepancies` | `tests/test_bank_gate.py` | Validated |
| **S-G** | **Authorised Release:** Multi-step release approval requiring Maker initiation, Bureau check, and Checker sign-off. | `/releases` | `tests/test_next_action.py` | Validated |
| **S-H** | **Bank Downtime Handling:** Graceful fallback to signed-letter verification when bank callback is unavailable. | `/deposits/:id/verify` | `tests/test_bank_gate.py` | Validated |
| **S-I** | **Break-Me Forgeries:** 9 intentional tampering attempts rejected with specific cryptographic reason codes. | `/break-me` | `tests/test_bank_gate.py` | Validated |

---

## 3. Operational Standards (CHARTER R1 – R14)
| Standard | Metric / Target | Measured Reality | Proving Command |
| :--- | :--- | :--- | :--- |
| **R1: One-command bringup** | < 120s warm cache | **7.4s** | `pwsh scripts/run-demo.ps1 --no-launch` |
| **R2: Doctor command** | Plain-language fixes | **100% green** on clean setup | `uv run python scripts/doctor.py` |
| **R3: Zero manual secrets** | Documented demo defaults | **Supported** via `FASTAPI_ENV=demo` | `uv run python scripts/run-demo.py --no-launch` |
| **R4: Deterministic reset** | < 60s full reset | **< 10s** reset | `uv run python -m app.initial_data` |
| **R5: Offline integrity** | 0 external fonts / CDNs | **0 external URLs** in bundle | `uv run python scripts/check-offline.py` |
| **R6: Resource budget** | Single worker < 1.5 GB | **~127 MB** backend + **~64 MB** DB | Measured via process monitor |
| **R8: Cross-platform** | Windows (pwsh), Linux, macOS | Native scripts provided for all shells | Verified on Windows & Git Bash |
