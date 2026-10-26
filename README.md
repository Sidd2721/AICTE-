# AICTE Security Deposit / Fixed Deposit Receipt (FDR) Portal

High-assurance regulatory portal prototype for AICTE Problem Statement PS 26265 (Monitoring and Verification of Fixed Deposit Receipts).  
Automates institutional security deposit submissions, independent cryptographic bank confirmations, automated renewal/expiry monitoring, and strict dual-custody release authorization.  
Engineered with defense-in-depth: Python 3.14, PostgreSQL Row-Level Security (`NOSUPERUSER`), SHA-256 hash-chained audit ledger, integer-paise accounting, and cryptographic bank confirmation gates.

---

## Try It

| Experience | How to Run | Description |
| :--- | :--- | :--- |
| **Instant Public Share (Track 1)** | `powershell -ExecutionPolicy Bypass -File scripts/share.ps1` | Spawns a secure public HTTPS Cloudflare Tunnel (`https://*.trycloudflare.com`) to show evaluators immediately. |
| **Always-On VM Deployment (Track 2)** | `docker compose -f deploy/docker-compose.demo.yml up -d` | Self-contained production demo with Caddy automatic TLS, Mailpit simulator, and PostgreSQL RLS. |
| **One-Command Local Showcase** | `powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset` | Resets database, seeds rich synthetic data, and plays all 7 problem-statement showcase scenarios. |
| **6-Minute Guided Tour** | Visit `http://localhost:8000/guide` | Interactive 7-step tour guide with plain-language walkthrough, persona switching, and glossary. |

---

## Primary Documentation Links

- [DEMO.md](DEMO.md) — 7-step live evaluation script synchronized with `docs/guide.json`.
- [docs/PRESENT.md](docs/PRESENT.md) — 30s pitch, 2-minute locker analogy, 6-minute live script, and Q&A cheat sheet.
- [docs/DEPLOY.md](docs/DEPLOY.md) — Always-on demo operations, multi-stage Docker build, and Caddy reverse proxy setup.
- [docs/EVIDENCE.md](docs/EVIDENCE.md) — Verifiable evidence map, mutation testing records, and system invariants.

---

## Honest Prototype Limits & Non-Claims

- **DEMO Rule Values**: Table 1.4 Approval Process Handbook rules are marked `DEMO` pending official council gazette confirmation; startup is blocked outside development/demo.
- **SIMULATED Bank & Email**: Bank confirmation APIs and email notices are SIMULATED and transparently labelled.
- **Synthetic Data Only**: All institutions, deposit amounts, reference numbers, and metrics are synthetic.
- **No Direct Banking Network**: Does not connect to live SFMS, RTGS, or RBI Core Banking Systems without regulatory MOUs.
- **Dual-Control Release**: The system provides automated recommendations; release authorization requires human approval.

---

## Proposed Integrations (Design Only)

These are ports for a future agreement, not live connections. Every current adapter is a labelled simulator.

| Integration Point | Protocol / Standard | Production Role in AICTE Ecosystem |
| :--- | :--- | :--- |
| **Bank confirmation** | Bank-hosted API over mutual TLS, or another agreed messaging channel | Return the same signed confirmation fields through a bank-approved adapter. |
| **AICTE institution directory** | Versioned bulk API with scoped machine key | Synchronize Permanent Institute IDs, regions and rule-backed programmes. |
| **AICTE identity** | OIDC single sign-on (target) | Map agreed claims to role, region and institution. |
| **Notifications** | Government e-mail gateway (target) | Replace the local Mailpit simulator after an agreement. |

---

## Seed Matrix & Contracted Personas

The portal is seeded with a dual-region, dual-custody maker-checker matrix:

| Role | Contracted Email | Region | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Institution** | `inst.north1@example.com` | North (NR) | Submits FDR details, views Table 1.4 coverage card, requests releases. |
| **Regional Officer (Maker)** | `officer.north@example.com` | North (NR) | Scrutinizes submissions, verifies releases (strictly blocked from approving). |
| **Regional Checker** | `checker.north@example.com` | North (NR) | Verifies regional officer recommendations (maker-checker separation). |
| **Bureau Approver (Checker)** | `bureau@example.com` | National | Advances system clock, approves verified releases (Maker != Checker). |
| **External Auditor** | `auditor@example.com` | National | Read-only oversight across all regions; verifies SHA-256 audit ledger. |
| **System Admin** | `admin@example.com` | National | User provisioning and system rule inspection. |

*Default password for demo personas: `changethis` (guarded against default values outside development).*

---

## System Safety Invariants (I1–I15)

- **I1: Runtime Database Role**: PostgreSQL runtime role has `NOSUPERUSER` and `NOBYPASSRLS`.
- **I2: Context Enforced**: `set_rls_context()` must be executed on every authenticated connection.
- **I3: Row Isolation**: Missing or invalid RLS context returns 0 rows (fail-closed).
- **I4: Append-Only Audit**: Direct writes to `audit_event` are blocked by database triggers; only `audit_append()` is permitted.
- **I5: Tamper-Evident Ledger**: The audit hash chain is cryptographically linked via SHA-256 (`audit_verify()`).
- **I6: Full Bank Gate**: Bank replies pass only through the full cryptographic verification gate.
- **I7: Dated Rules Engine**: Rules are versioned JSON; files marked DEMO block startup in production.
- **I8: Maker-Checker**: `verified_by <> approved_by` is strictly enforced in code and database triggers.
- **I9: Human Authorization**: System recommendations are advisory; release tokens are issued only by authorized humans.
- **I10: Integer Money**: All financial calculations use integer paise (`bigint`). Zero floating-point rounding.
- **I11: Dynamic Next Action**: Primary workflow buttons are served by `next_action()` backend logic.
- **I12: Privacy & Leak Protection**: No secrets, PII, or real FDR numbers in git, logs, or test fixtures.
- **I13: Formula Injection Protection**: All CSV exports sanitize formula-trigger characters (`=`, `+`, `-`, `@`).
- **I14: Python 3.14 Standard**: Native modern syntax (`except A, B:`) strictly preserved.
- **I15: Distributed Rate Limiting**: Shared PostgreSQL-backed sliding window rate limiting on sensitive endpoints.

---

## Verification & Quality Gate

```powershell
# Run the complete quality gate (tests, types, linter, build, leak and claim checks)
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1

# Run the standalone deployed smoke suite
uv run python scripts/smoke_deployed.py http://localhost:8000
```
