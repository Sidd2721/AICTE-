# Render 24/7 Deployment Runbook

This guide describes how to configure, deploy, and maintain the AICTE Security Deposit Portal on Render as an always-on service.

---

## 1. Hosting Plan & Resource Allocation

### Always-On Production Recommendation (Starter Tier or Higher)
- **Runtime**: Docker Web Service
- **Instance Plan**: Starter (or higher)
- **RAM**: 512 MB to 2 GB
- **Persistent Disk**: 10 GB mounted at `/app/backend/vault`
- **Region**: Singapore (`singapore` / `ap-southeast-1`), closest to Indian institutional traffic.

> [!NOTE]
> **Pricing Notice**: Pricing and plan specifications change over time. Please verify current rates and disk add-on costs directly on the official Render pricing page at `render.com/pricing` before provisioning resources.

### Free-Tier Fallback Limitations
If deployed on Render's Free tier using `render.free-fallback.yaml`:
- **Inactivity Spin-down**: The service suspends automatically after 15 minutes without inbound requests.
- **Cold Boot Delay**: The first request after spin-down takes approximately 50 to 70 seconds to wake the container.
- **Ephemeral Storage**: Files written to `/app/backend/vault` inside the container are permanently destroyed whenever the instance sleeps, restarts, or redeploys. To avoid document loss on free tier, configure external object storage (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`).
- **RAM Ceiling**: Hard limit of 512 MB. Memory overruns trigger SIGKILL OOM termination.

---

## 2. Persistent Disk Configuration
On the Starter plan (or higher), attach a persistent disk to preserve encrypted deposit receipts across deployments:
- **Disk Name**: `fdr-vault-disk`
- **Mount Path**: `/app/backend/vault`
- **Initial Size**: 10 GB
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
| `DATABASE_URL` | Yes | `postgresql://user:pass@host:5432/dbname` | Application connection string (Session Pooler recommended). |
| `SECRET_KEY` | Yes | 64-character hex or base64 string | Session token signing key. |
| `VAULT_KEY` | Yes | 32-byte base64 encoded string | Dedicated AES-256-GCM encryption key. |
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
- **Response**: Returns HTTP 200 `{"status":"ready"}` only if:
  1. PostgreSQL responds to `SELECT 1`.
  2. The applied migration revision matches Alembic `head`.
  3. The `/app/backend/vault` directory is writable by `appuser`.
- Returns HTTP 503 `{"status":"unready"}` if any dependency is degraded.

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

## 7. Demo-Day Pre-Flight Checklist
Execute these checks 30 minutes before evaluating or presenting:
1. [ ] **Service Awake**: Open `https://your-service.onrender.com/health` in a browser and verify HTTP 200 with `status: ok`.
2. [ ] **Readiness Probe**: Query `https://your-service.onrender.com/ready` and confirm `status: ready`.
3. [ ] **Disk Attached**: In Render Dashboard **Disks** tab, confirm `fdr-vault-disk` is mounted at `/app/backend/vault`.
4. [ ] **Demo Personas**: Access `https://your-service.onrender.com/login` and verify 1-click persona buttons are visible.
5. [ ] **Audit Trail Continuity**: Navigate to `/audit` and click **Verify Hash Chain** to confirm mathematical integrity.
