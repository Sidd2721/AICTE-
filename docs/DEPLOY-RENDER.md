# Render 24/7 Deployment Runbook

This guide describes how to configure, deploy, and maintain the AICTE Security Deposit Portal on Render as an always-on service.

---

## 1. Hosting Plan & Resource Allocation

### Always-On Production Architecture (Render Web Service + Neon PostgreSQL)
- **Web Service Name**: `aicte-fdr-portal`
- **Runtime**: Docker Web Service
- **Instance Plan**: `starter` (or `free` if persistent disk is omitted)
- **Database Engine**: Neon PostgreSQL 16 (`DB_HOST_KIND=neon-direct`)
  - **Connection Mode**: DIRECT (non-pooler) hostname (`ep-xxxx.region.aws.neon.tech`).
  - **CRITICAL SECURITY REQUIREMENT**: The pooled string (`-pooler.`) is **strictly unsafe** and forbidden. Neon's connection pooler uses PgBouncer transaction mode, which strips session variables (`set_config('app.role', ...)` and `set_config('app.region', ...)`) between statements. This breaks Row-Level Security (RLS) isolation and causes cross-tenant bleeding. Additionally, pooled connections cannot maintain PostgreSQL advisory locks (`pg_try_advisory_lock(847291)`). If `neon-pooler` is configured: **STOP deployment immediately**.
- **RAM**: 512 MB to 2 GB
- **Persistent Disk**: OPTIONAL (see Section 2).
- **Region**: Singapore (`singapore` / `ap-southeast-1`), closest to Indian institutional traffic.

> [!NOTE]
> **Render-Managed PostgreSQL Variant**: If you choose Render's built-in managed PostgreSQL database instead of Neon, use the blueprint file `render.render-postgres.yaml`.

### Free-Tier Fallback Limitations
If deployed on Render's Free tier using `render.free-fallback.yaml`:
- **Inactivity Spin-down**: The service suspends automatically after 15 minutes without inbound requests.
- **Cold Boot Delay**: The first request after spin-down takes approximately 50 to 70 seconds to wake the container.
- **Ephemeral Storage**: Files written to `/app/backend/vault` inside the container are permanently destroyed whenever the instance sleeps, restarts, or redeploys. To avoid document loss on free tier, configure external object storage (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`).
- **RAM Ceiling**: Hard limit of 512 MB. Memory overruns trigger SIGKILL OOM termination.

---

## 2. Persistent Disk Configuration (Optional vs Rolling Deploys)
Attaching a persistent disk (`fdr-vault-disk`) to the web service is **OPTIONAL**:
- **With a persistent disk**:
  - Provides local POSIX storage for encrypted deposit receipts at `/app/backend/vault`.
  - **Redeploy Trade-off**: Redeployments cause a **short service outage** because Render must stop the existing instance before detaching and mounting the disk onto the new container instance.
- **Without a persistent disk**:
  - Deploys are **zero-downtime rolling deploys** (the new instance boots, passes `/health` and `/ready`, and only then replaces the old instance).
  - Encrypted documents are synced directly to cloud object storage using Supabase S3 (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET=fdr-vault`).
- **Disk Specifications (if enabled)**:
  - **Disk Name**: `fdr-vault-disk`
  - **Mount Path**: `/app/backend/vault`
  - **Initial Size**: 1 GB
  - **Environment Variable**: `VAULT_PATH=/app/backend/vault`

> [!WARNING]
> **Vault Key Immutability**: The encryption key stored in `VAULT_KEY` must never be altered or rotated after initial setup. Altering `VAULT_KEY` renders existing `.enc` files in the vault permanently unreadable.

---

## 3. Environment Variables Reference
Configure these variables in your Render Service Dashboard (**Environment** tab). Never commit secrets to source code.

| Variable Name | Required | Recommended Value / Format | Purpose |
| :--- | :--- | :--- | :--- |
| `FASTAPI_ENV` | Yes | `demo` or `production` | Enforces regulatory guards, persona visibility, and rules file locks. |
| `PROJECT_NAME` | Yes | `AICTE Security Deposit Portal` | Display name across headers and responses. |
| `PORT` | Yes | `10000` | Port on which the container listens (Render default). |
| `WEB_CONCURRENCY` | Yes | `1` | Worker processes count. Keep at 1 for 512 MB memory footprint. |
| `VAULT_PATH` | Yes | `/app/backend/vault` | Filesystem path for encrypted AES-256-GCM receipts. |
| `TRUSTED_PROXY_HOPS` | Yes | `1` | Configures client IP resolution through Render's reverse proxy. |
| `DATABASE_URL` | Yes | `postgresql://app:<app_pw>@ep-xxxx.region.aws.neon.tech/neondb` | Neon **DIRECT (non-pooler)** application connection string with restricted `app` role. Never use pooled string. |
| `MIGRATION_DATABASE_URL` | Yes | `postgresql://neondb_owner:<owner_pw>@ep-xxxx.region.aws.neon.tech/neondb` | Neon **DIRECT** owner connection string for Alembic schema migrations. |
| `SECRET_KEY` | Yes | 64-character hex or base64 string | Session token signing key. |
| `VAULT_KEY` | Yes | 44-character base64 string (32 raw bytes) | Dedicated AES-256-GCM encryption key. Generate via: `python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"` |
| `AUTO_SEED` | No | `true` (demo) / `false` (prod) | Triggers background demo data seeding on initial run. |
| `FRONTEND_HOST` | No | `https://your-service.onrender.com` | Allowed CORS origin for the browser application. |
| `SUPABASE_URL` | Optional | `https://<ref>.supabase.co` | Optional secondary cloud vault sync. |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | JWT service token | Optional secondary cloud vault sync. |
| `SUPABASE_STORAGE_BUCKET` | Optional | `fdr-vault` | S3-compatible bucket name. |

---

## 4. Health Check & Monitoring Strategy

### Liveness Probe (Render Dashboard Setting)
- **Health Check Path**: `/health`
- **Interval**: Render monitors this every few seconds.
- **Why `/health`**: It is an in-memory route that does not execute database queries or disk scans. If PostgreSQL experiences transient latency or cold pool connection refreshes, Render will not prematurely restart the container.

### Readiness Probe (Deep Diagnostic)
- **Endpoint**: `/ready`
- **Characteristics**: Excluded from the public OpenAPI schema to maintain contract stability.
- **Response**: Returns HTTP 200 `{"status":"ready","build":"<commit_7>"}` only if:
  1. PostgreSQL responds to `SELECT 1`.
  2. The applied migration revision matches Alembic `head`.
  3. The `/app/backend/vault` directory is writable by `appuser`.
- **Build Identification**: Contains `"build"` reflecting the first 7 characters of `RENDER_GIT_COMMIT` (or `"unknown"` if unset).
- **Deployment Verification Loop**: Poll `/ready` every 30 s (max 20 min) until `"build"` equals the first 7 characters of the merge commit on `main`. A 200 with another build does not count as a completed deployment.
- Returns HTTP 503 `{"status":"unready","build":"<commit_7>"}` if any dependency is degraded.

---

## 5. Inspection & Observability

In your Render dashboard:
- **Logs**: Located under the **Logs** tab. Shows structured startup timing (`[start.sh]`, `[lifespan]`), migration execution, and incoming HTTP access logs.
- **Events**: Located under the **Events** tab. Displays container start, deploy progress, health check failures, and port detection status.
- **Metrics**: Located under the **Metrics** tab. Monitors CPU utilization and RAM consumption. On a 512 MB plan, ensure memory stays below 420 MB.

---

## 6. Rollback Procedure
If a deployment exhibits degraded behavior:
1. Navigate to the **Deploys** tab on the Render Dashboard.
2. Identify the previous green deploy commit.
3. Click the three dots (`...`) next to that deploy and select **Rollback to this deploy**.
4. Render immediately pulls and restarts the previous verified container image without rebuilding.

---

## 7. Real Client IP & Header Validation
Render's public documentation confirms that its reverse proxy appends incoming client IPs to `X-Forwarded-For`. Render does **not** officially guarantee `True-Client-IP` across all edge configurations.

To validate your deployed service's client IP detection:
1. **Two-Network Test**:
   - Send a request from laptop broadband (Network A) and one from mobile cellular data (Network B).
   - In Render Logs, verify that requests show two distinct public IP addresses rather than Render's internal proxy IP.
2. **Forged Header Anti-Bypass Test**:
   - Send a test request with a spoofed header:
     ```bash
     curl -H "X-Forwarded-For: 1.1.1.1" https://your-service.onrender.com/api/health
     ```
   - With `TRUSTED_PROXY_HOPS=1`, the application takes the last hop appended by Render's proxy, ignoring the client-supplied `1.1.1.1`.
3. **True-Client-IP Notice**:
   - A client-supplied `True-Client-IP` header is **never trusted** when `TRUSTED_PROXY_HOPS=0`. When `TRUSTED_PROXY_HOPS > 0`, `X-Forwarded-For` traversal remains the authoritative fallback.

---

## 8. Demo-Day Pre-Flight Checklist
Execute these checks 30 minutes before evaluating or presenting:
1. [ ] **Service Awake**: Open `https://your-service.onrender.com/health` in a browser and verify HTTP 200 with `status: ok`.
2. [ ] **Readiness Probe**: Query `https://your-service.onrender.com/ready` and confirm `status: ready`.
3. [ ] **Disk Attached**: In Render Dashboard **Disks** tab, confirm `fdr-vault-disk` is mounted at `/app/backend/vault`.
4. [ ] **Demo Personas**: Access `https://your-service.onrender.com/login` and verify 1-click persona buttons are visible.
5. [ ] **Audit Trail Continuity**: Navigate to `/audit` and click **Verify Hash Chain** to confirm mathematical integrity.

---

## 9. Offline Secret Backups & Key Loss Warnings
> [!CAUTION]
> **VAULT_KEY is Unrecoverable**: Store copies of `VAULT_KEY` and `SECRET_KEY` in a secure offline password manager (e.g. Bitwarden, 1Password, or encrypted HSM). If `VAULT_KEY` is lost or rotated, all existing encrypted documents in the vault become permanently lost.

---

## 10. Database Backups & Point-in-Time Restore
Render managed PostgreSQL on paid plans (`0.1c-256mb` / Starter) includes automated daily backups:
1. **Backups Tab**: Navigate to `aicte-fdr-db` in the Render dashboard and click **Backups**.
2. **Snapshot Retention**: Daily automated snapshots are retained for 7 days.
3. **Manual Backup**: Trigger an ad-hoc backup anytime via the dashboard before applying major operational changes.
4. **Restore Procedure**:
   - To restore, select the backup timestamp and choose **Restore to a New Database**.
   - Update `DATABASE_URL` in your web service to point to the newly restored instance.

---

## 11. Production Smoke Verification Script
Run the automated production verification suite from any terminal with `curl`:
```bash
bash scripts/smoke_prod.sh https://aicte-1-59pn.onrender.com
```
This script verifies:
1. HTTP 200 on `/health` (Liveness)
2. HTTP 200 on `/ready` (Readiness)
3. HTTP 200 on persona authentication (`inst.north1@example.com`)
4. HTTP 401/403 authorization guard on protected endpoints (`/api/v1/instruments/`)
5. Presence of mandatory HTTP security headers (`x-content-type-options`, `x-frame-options`, `referrer-policy`)

---

## 12. External Monitoring Configuration
- **Liveness Ping**: Configure UptimeRobot (or BetterStack) to ping `https://your-service.onrender.com/health` every 5 minutes. This keeps the service warm and tracks true uptime.
- **Readiness Diagnostic**: Optionally configure an alert-only probe on `https://your-service.onrender.com/ready` every 5 minutes.
- **Alert Routing**: Direct failure notifications to your platform operations email or Slack channel.

---

## 13. Managed PostgreSQL RLS Role Setup (BLOCKER for Owner)
> [!IMPORTANT]
> **Owner RLS Bypass Guard**: In PostgreSQL, the role that owns a table automatically bypasses Row-Level Security policies unless `FORCE ROW LEVEL SECURITY` is set.
> On Render, the default connection string connects as the database owner.
> To enforce Invariant I4 (NOSUPERUSER, NOBYPASSRLS) and prevent RLS bypass, execute this one-time SQL script connected as the database owner (`psql <RENDER_POSTGRES_DIRECT_URL>`):

```sql
-- 1. Create dedicated restricted application runtime role
CREATE ROLE app LOGIN PASSWORD 'replace_with_strong_runtime_password' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE app TO app;
GRANT USAGE ON SCHEMA public TO app;

-- 2. Grant least-privilege DML access to app (no TRUNCATE, no DDL)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;

-- 3. Set default privileges for tables created during future migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app;

-- 4. Verify role attributes (both rolsuper and rolbypassrls MUST be false)
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app';
```

After creating the role, update the `DATABASE_URL` environment variable in the web service:
```
postgresql://app:replace_with_strong_runtime_password@dpg-xxxx-a.singapore-postgres.render.com/app
```

---

## 14. First Superuser Password Rotation
After initial deployment:
1. Log in to `https://your-service.onrender.com/login` using `FIRST_SUPERUSER` (`admin@example.com`).
2. Navigate to **Settings** -> **Change Password**.
3. Update the administrator credentials to a strong unique passphrase.
4. In the Render Dashboard **Environment** tab, update `FIRST_SUPERUSER_PASSWORD` to match or revoke the initial seed value.
