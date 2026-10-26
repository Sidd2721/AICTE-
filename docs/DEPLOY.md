# Deployment & Operations Guide — AICTE FDR Portal

**Prototype for Government Regulator (AICTE PS 26265)**  
*Sprint 2 Track 2: Always-On Demo Deployment*

---

## 1. Overview & Architecture

The AICTE Fixed Deposit Receipt (FDR) Portal can be deployed as an always-on, self-contained demonstration environment on any Linux VM or cloud server using Docker Compose and Caddy.

```
 Internet (Browser / Evaluator)
           │
           ▼
    [ Caddy Reverse Proxy ] (Automatic HTTPS / TLS)
     :80, :443
           │
     ┌─────┴──────────────────────┐
     │                            │
     ▼                            ▼
[ api:8000 ]                 [ mailpit:8025 ]
FastAPI + Compiled React SPA  Email Simulator UI
     │
     ▼
[ db:5432 ]
PostgreSQL 16 (RLS + Append-Only Trigger)
```

### Components
1. **`caddy`**: Modern reverse proxy handling automatic HTTPS, TLS certificates, and security headers.
2. **`api`**: Single multi-stage container running Python 3.14 + Uvicorn serving both the FastAPI REST API and the compiled React 19 single-page application.
3. **`db`**: PostgreSQL 16 database with Row-Level Security (RLS) policies and append-only cryptographic triggers.
4. **`migrate`**: Ephemeral initialization container running database schema migrations (`alembic upgrade head`) and seeding rich synthetic data.
5. **`mailpit`**: In-cluster SMTP server and web inbox simulator for testing verification notices without outbound email risk.

---

## 2. Quickstart Deployment

### Prerequisites
- Docker Engine 24+ and Docker Compose v2.20+
- Python 3.10+ (for secret generation and smoke testing)
- A domain name pointing to your server's public IP (or `localhost` for local testing)

### Step 1: Clone Repository
```bash
git clone https://github.com/aicte-portal/fdr-portal.git
cd fdr-portal
```

### Step 2: Generate Cryptographic Secrets
Never use default credentials in deployments. Generate cryptographically strong keys using the provided utility:

```bash
python scripts/gen_secrets.py --output deploy/.env.demo --domain demo.example.com
```

This generates:
- 32-byte URL-safe `SECRET_KEY`
- 32-byte Base64 `VAULT_KEY` (AES-256-GCM)
- High-entropy `POSTGRES_PASSWORD` and `FIRST_SUPERUSER_PASSWORD`

### Step 3: Launch Containers
```bash
docker compose -f deploy/docker-compose.demo.yml --env-file deploy/.env.demo up -d --build
```

The startup sequence automatically:
1. Builds the frontend React application with Bun.
2. Installs Python dependencies in the runtime image.
3. Awaits database health check.
4. Runs schema migrations and seeds standard demo personas.
5. Starts the FastAPI server and Caddy TLS proxy.

---

## 3. Post-Deployment Verification

Run the standalone smoke test suite to verify end-to-end functionality (standard library only; no external dependencies required):

```bash
python scripts/smoke_deployed.py https://demo.example.com
```

The smoke suite verifies:
1. `GET /api/v1/utils/health-check` (API operational)
2. `GET /` (React SPA shell delivered)
3. `GET /api/v1/meta` (Transparency banner data without secret leakage)
4. Security headers (`nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`)
5. Persona authentication for all 4 roles (`institution`, `regional`, `bureau`, `auditor`)
6. Dashboard regulatory counters and cryptographic hash chain integrity
7. Brute force rate limiting defense (`HTTP 429`)

---

## 4. Operational Maintenance & Demo Reset

To restore the demo to its pristine state (e.g. between evaluator sessions):

```bash
bash scripts/reset_demo.sh
```

Or run via Docker Compose:
```bash
docker compose -f deploy/docker-compose.demo.yml exec api uv run python -m app.initial_data
docker compose -f deploy/docker-compose.demo.yml exec api uv run python scripts/demo_steps.py
```

---

## 5. Environment Variables Reference

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `FASTAPI_ENV` | Yes | Operating environment mode (`demo` or `development`) | `demo` |
| `SECRET_KEY` | Yes | 32+ byte key for signing authentication JWT tokens | `(Generated)` |
| `VAULT_KEY` | Yes | 32-byte Base64 key for encrypting sensitive fields | `(Generated)` |
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql+psycopg://...` |
| `FIRST_SUPERUSER` | Yes | Initial administrator email | `admin@example.com` |
| `FIRST_SUPERUSER_PASSWORD` | Yes | Initial administrator password | `(Generated)` |
| `DOMAIN` | No | Domain name for Caddy automatic TLS | `demo.example.com` |
| `SMTP_HOST` | No | SMTP relay server (defaults to `mailpit`) | `mailpit` |
| `SMTP_PORT` | No | SMTP relay port | `1025` |

---

## 6. Security & Hardening Assurances

1. **Guarded Secrets**: In `FASTAPI_ENV=demo`, the backend enforces 32-byte minimum key lengths and rejects `changethis` placeholder passwords during startup.
2. **Hidden Documentation**: `/docs` and `/openapi.json` are disabled (`404 Not Found`) in demo mode to protect API surface area from casual discovery.
3. **Database RLS**: Application connections use a restricted database role (`NOSUPERUSER`, `NOBYPASSRLS`). The session RLS context must be explicitly set before any institutional rows are returned.
4. **Append-Only Ledger**: The `audit_event` table is locked by database triggers blocking `UPDATE`, `DELETE`, and `TRUNCATE`.
