# AICTE Security Deposit / Fixed Deposit Receipt (FDR) Portal

> **AICTE Problem Statement PS 26265**  
> **Evaluation & Submission Prototype**  
> *Notice: All data in this repository and demo instances is synthetic. Bank integrations, university registries, and regulatory approval workflows are labelled simulators. No real money moves.*

---

## 1. System Overview

The **AICTE Security Deposit / FDR Portal** is a high-assurance regulatory compliance portal built for the All India Council for Technical Education (AICTE) to automate the submission, independent bank verification, monitoring, and dual-custody release of institutional security deposits.

### Core Capabilities
- **Institutional Self-Service**: Multi-step submission flow with client-side magic-bytes file validation, SHA-256 deduplication, and AES-256-GCM encrypted document vault storage.
- **Dynamic Trust Engine**: Continuous trust classification (`claimed`, `confirmed`, `stale`, `changed`) based on immutable verification provenance.
- **Cryptographic Bank Gate (Invariant I3)**: Full 6-point verification for bank confirmation replies (cryptographic PDF signatures, root trust chains, non-repudiation key usage, byte-prefix continuity, and pinned authority matching).
- **Dual-Custody Release (Invariant I6)**: Strict maker-checker enforcement (`verified_by <> approved_by`) preventing single-operator release of funds.
- **Append-Only Audit Ledger (Invariant I4)**: Cryptographic SHA-256 hash-chained audit trail (`audit_append()`) with runtime tamper-detection (`audit_verify()`).
- **Postgres-Backed Rate Limiting**: Shared sliding-window throttling across all worker processes for authentication, recovery, and bank reply routes.
- **Integer Money (Invariant I5)**: 100% of calculations, database storage, and API contracts operate in integer **paise** (`bigint`) with zero floating-point arithmetic.

---

## 2. Technology Stack

- **Backend**: Python 3.14 (`except A, B:` syntax), FastAPI, SQLModel, Alembic, PyHanko, PyHanko-Certvalidator, Cryptography 50.0.2, ReportLab.
- **Database**: PostgreSQL 16 (`postgres:16`) with Row-Level Security (RLS) and strict role separation:
  - `migrator`: DDL schema owner (migration-only).
  - `app`: Runtime user (`NOSUPERUSER`, `NOBYPASSRLS`).
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, shadcn/ui.
- **Code Generation**: Hey-API OpenAPI client (`@hey-api/openapi-ts`) generated strictly from backend schemas.

---

## 3. Seed Matrix & Test Credentials

The portal is seeded with a dual-region, dual-custody maker-checker matrix (`backend/app/core/db.py`):

| Role | Email | Region / Scope | Responsibilities |
|---|---|---|---|
| **Regional Officer** | `officer.north@aicte.gov.in` | North Region | Scrutinizes submissions, raises discrepancy requests, recommends release. |
| **Regional Checker** | `checker.north@aicte.gov.in` | North Region | Verifies officer recommendations (maker-checker). |
| **Institution** | `inst1.north@example.edu` | North Region | Submits FDR details, renews deposits, views obligations. |
| **Institution** | `inst2.north@example.edu` | North Region | Second institution in North region (demonstrates regional isolation). |
| **Regional Officer** | `officer.west@aicte.gov.in` | West Region | Scrutiny in West region (RLS blocks access to North). |
| **Regional Checker** | `checker.west@aicte.gov.in` | West Region | Checker in West region. |
| **Institution** | `inst1.west@example.edu` | West Region | Institution in West region. |
| **Bureau Head** | `bureau@aicte.gov.in` | National | Approves releases, monitors national compliance. |
| **Auditor** | `auditor@aicte.gov.in` | National | Read-only oversight across all regions and institutions. |
| **Administrator** | `admin@aicte.gov.in` | System | System administration, rule management, and user provisioning. |

*Default password for all demo accounts in development: `changethis` (configured via `.env`).*

---

## 4. Quickstart & Local Setup

### Prerequisites
- Python 3.14
- `uv` package manager (`pipx install uv` or `winget install astral-sh.uv`)
- `bun` runtime (`npm install -g bun` or `winget install Oven-sh.Bun`)
- Docker Desktop with Docker Compose

### Step 1: Clone and Configure Environment
```bash
git clone <repo-url> fdr-portal
cd fdr-portal

# Copy environment template
cp .env.example .env
```

### Step 2: Start PostgreSQL Database
```bash
docker compose up -d db
```
The database runs on `localhost:5432` with volume mounted at `/var/lib/postgresql/data`.

### Step 3: Install Dependencies
```bash
# Backend dependencies
cd backend
uv sync

# Frontend dependencies
cd ../frontend
bun install
```

### Step 4: Run Migrations and Turnkey Seed Data
```bash
cd ../backend
uv run alembic upgrade head
uv run python -m app.initial_data
```

### Step 5: Start Development Servers
In separate terminals:

```bash
# Terminal 1 — Backend (http://localhost:8000)
cd backend
FASTAPI_ENV=development uv run fastapi dev app/main.py

# Terminal 2 — Frontend (http://localhost:5173)
cd frontend
bun run dev
```

---

## 5. Quality Gate & Automated Verification

Before any commit or slice delivery, the mandatory quality gate must pass without errors:

```bash
bash scripts/check.sh
```

The gate executes:
1. **Repository Hygiene**: Verifies `.env` is not tracked in git.
2. **Schema Verification**: Runs `alembic check` to detect uncommitted model migrations.
3. **Database Security Guard**: Asserts the runtime role `app` has `rolsuper=false` and `rolbypassrls=false`.
4. **Backend Test Suite**: Executes 96+ tests including all 10 bank-gate cryptographic forgery tests, CSV injection guards, dynamic trust logic, rate limiter tests, and hardening assertions.
5. **Backend Type Checking & Linting**: Executes `mypy app` and `ruff check app`.
6. **Frontend Linting & Typecheck**: Executes `bunx biome check` across all frontend code.
7. **Production Frontend Build**: Compiles React SPA production bundle.

---

## 6. Architecture & Hard Invariants (I1–I15)

- **I1: Python 3.14**: Uses native `except A, B:` syntax.
- **I2: Runtime RLS**: Role `app` has `NOSUPERUSER` and `NOBYPASSRLS`. Missing RLS context returns 0 rows.
- **I3: Bank Gate**: Requires valid signature, non-repudiation key usage, matching pinned authority, and exact byte-prefix matching.
- **I4: Audit Ledger**: Append-only via `audit_append()`; verified by hash-chain traversal.
- **I5: Integer Money**: All amounts in paise (`bigint`). Zero floats.
- **I6: Maker-Checker**: `verified_by <> approved_by` enforced on release and scrutiny workflows.
- **I7: Dated Rules**: All deposit amounts are loaded from versioned JSON rulebooks; DEMO files block startup in production.
- **I8: Dynamic Next Action**: Primary workflow buttons are served by `next_action()` backend logic.
- **I9: Privacy & Secrets**: No real FDR numbers, PII, or secrets in git, logs, or test fixtures.
- **I10: File Validation**: Magic bytes validation prevents disguised file uploads.
- **I11: Token Lifetime**: Access tokens expire in 60 minutes.
- **I12: Dynamic Trust**: Computed dynamically (`claimed`, `confirmed`, `stale`, `changed`).
- **I13: Distributed Rate Limiting**: Shared Postgres-backed rate limiting.
- **I14: CSV Sanitization**: Formula injection neutralized via `csv_safe`.
- **I15: Vault Encryption**: AES-256-GCM authenticated encryption with record-bound AAD.

---

## 7. License
Prototype developed for AICTE Problem Statement PS 26265.
