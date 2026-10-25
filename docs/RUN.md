# AICTE Deposit/FDR Portal (PS 26265) — RUN GUIDE

One-page guide to running, testing, and verifying the AICTE Security Deposit & FDR Portal prototype.

---

## 1. Prerequisites (Doctor Command)
Before starting, verify your environment with the Doctor command (CHARTER R2):

**Windows (PowerShell):**
```powershell
pwsh scripts/doctor.ps1
```

**Linux / macOS / Git Bash:**
```bash
bash scripts/doctor.sh
```

The doctor verifies:
- Python >= 3.14 (Invariant I1)
- `uv` package manager
- `bun` runtime for frontend
- Docker engine / container runtime
- Port availability: 5432 (Postgres), 8000 (Backend API), 5173 (Vite frontend)
- Free disk space (> 2 GB)
- Invariant I9 (.env untracked in git)

---

## 2. One-Command Demo Bring-Up (CHARTER R1)
To bring up a running, fully-seeded demo stack with a single worker under 1.5 GB RAM:

**Windows (PowerShell):**
```powershell
pwsh scripts/run-demo.ps1
```

**Linux / macOS / Git Bash:**
```bash
bash scripts/run-demo.sh
```

This command:
1. Executes the system doctor checks.
2. Starts or connects to PostgreSQL on port 5432.
3. Runs database migrations (`alembic upgrade head`).
4. Seeds deterministic dual-custody accounts (all passwords: `changethis`).
5. Launches the single-worker backend serving both API and compiled SPA on `http://localhost:8000`.

---

## 3. Seeded Demo Accounts (Password: `changethis`)
| Role | Email | Region / Institution | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Officer** | `officer.north@example.com` | Northern Region | Maker: Review FDRs, flag discrepancies, draft release |
| **Checker** | `checker.north@example.com` | Northern Region | Checker: Dual-custody approve/reject releases (Maker ≠ Checker) |
| **Officer** | `officer.west@example.com` | Western Region | Regional isolation verification (cannot see Northern records) |
| **Institution** | `inst.north1@example.com` | Tech Inst #1 (North) | Submit FDRs, track approvals, view obligations & renewals |
| **Bureau** | `bureau@example.com` | AICTE Headquarters | National overview, macro analytics, rule threshold editor |
| **Auditor** | `auditor@example.com` | Empanelled Auditor | Read-only audit chain verification (`audit_append` hash checks) |
| **Admin** | `admin@example.com` | System Admin | System status, simulator toggles, database health |

---

## 4. Verification Gate
To run the complete verification gate:
```bash
bash scripts/check.sh
```
Checks performed:
1. `.env` untracked guard
2. Migration status (`alembic check`)
3. Database role flags (`app` role must have `rolsuper=false` and `rolbypassrls=false`)
4. Backend test suite (`FASTAPI_ENV=development uv run pytest -q`)
5. Backend lint and type safety (`mypy app` + `ruff check app` + `ruff format --check app`)
6. Frontend biome lint & formatting (`bunx biome check`)
7. Frontend bundle build (`bun run build`)

---

## 5. Offline Integrity Check (CHARTER R5)
Verify that the compiled frontend has zero CDN or external web font dependencies:
```bash
uv run python scripts/check-offline.py
```

---

## 6. Troubleshooting Top 10
1. **Port 5432 already in use:** Stop existing local postgres service or update `.env` port mapping.
2. **Postgres container fails to start:** Ensure Docker Desktop is running and run `docker compose up -d db`.
3. **Database role permission errors:** Connect as superuser (`postgres`) and run `\i scripts/roles.sql` to re-create `migrator` and `app` roles.
4. **Mypy type errors with dict:** Use explicit typing `dict[str, Any]` and import `from typing import Any`.
5. **Alembic autogenerate detected unmigrated models:** Run `cd backend && uv run alembic revision --autogenerate -m "<msg>"` followed by `uv run alembic upgrade head`.
6. **Frontend biome lint errors:** Run `cd frontend && bunx biome check --write ./` to auto-fix styling and imports.
7. **SECRET_KEY error outside development:** Set a 32+ character key or use `FASTAPI_ENV=demo`.
8. **Git Bash executable error in WSL:** Run commands using native `uv run python` or execute directly in native bash/pwsh.
9. **RLS context returning zero rows:** Ensure `set_rls_context(session, role=..., region=..., institution=...)` is invoked right after user lookup.
10. **Reset seed data:** Run `uv run python scripts/run-demo.py --reseed --no-launch` to restore the pristine baseline state in under 10 seconds.
