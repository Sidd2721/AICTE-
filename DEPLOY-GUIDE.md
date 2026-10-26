# DEPLOY GUIDE — GitHub repo + free hosting + keys, step by step

Read `REVIEW.md` first (10 min): it says what I could and could not verify about your project and lists the things to fix **before** a public deploy.

**Honesty box.** I cannot see your repository (your report points at a folder on your Windows PC). Everything below about *your* code comes from your report. Everything marked **[RAN]** I executed against the FastAPI template your project is built on, using the same patterns (two DB roles, `prestart.sh`, `fastapi run`, built SPA folder). Everything marked **[SOURCE]** comes from public pages dated Sept–Oct 2026; free tiers change often, so check each provider's pricing page on the day you deploy. Everything marked **[NOT RUN]** I could not execute here (Docker, Render, Neon, GitHub Actions).

---

## Part 0 — The plan in one screen

| Piece | Choice | Why | Cost / card |
|---|---|---|---|
| Code | GitHub repo (public or private) | CI, history, deploy trigger | free |
| App host | **Render, free web service, Docker** | Runs your existing Dockerfile; one container serves API + SPA; TLS at the edge; no card **[SOURCE]** | free, no card |
| Database | **Neon, free plan** | Real Postgres 16, does not expire (Render's free Postgres expires after 30 days) **[SOURCE]** | free, no card |
| Secrets | Render env vars + GitHub Actions secrets | Never in git | free |
| Keys from third parties | **None required** | Bank/AICTE/NeSL parts are simulators; SPA loads nothing from outside (per your report) | — |

**Free-tier limits you must accept** **[SOURCE]**: Render free web service sleeps after 15 min idle and takes ~1 min to wake, has 512 MB RAM and a small CPU share, 750 instance-hours/month, no custom domain, no persistent disk. Neon free: 100 compute-hours and 0.5 GB per project, compute suspends after 5 min idle, and stops at the monthly limit. This is fine for a demo/evaluation, not for real institutions' data.

Alternatives checked **[SOURCE]**: Fly.io no free tier for new accounts; Railway only a small trial credit; Koyeb needs a card (reported $29 hold); Google Cloud Run has an always-free quota but needs a card. If you accept a card, Cloud Run + Neon also works with the same Dockerfile.

---

## Part 1 — Before you push: repo hygiene (30 min, do not skip)

Your report contains absolute links like `file:///c:/...` and mentions an agent folder (`.gemini/antigravity/...`). Those break on GitHub and leak your username. Run these in the repo root (Git Bash or WSL):

```bash
# 1. secrets must not be tracked
git ls-files | grep -E '(^|/)\.env$' && echo "!! .env is tracked"
git log --all --diff-filter=A --name-only --format= | grep -E '(^|/)\.env$' && echo "!! .env WAS committed in history -> rotate every secret in it"

# 2. local paths / personal info in tracked files
git grep -nE 'file:///|C:\\Users|/Users/[a-z]+/|avadu|\.gemini' -- . ':!*.lock' | head -50

# 3. private keys or tokens
git grep -nE 'BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY|api[_-]?key *= *["'"'"'][A-Za-z0-9]{16,}' -- . | head

# 4. big files (GitHub warns at 50 MB, blocks at 100 MB)
git ls-files -z | xargs -0 du -k 2>/dev/null | sort -rn | head -5
```

Fix what they print:
- Replace every `file:///c:/...` link with a **relative** link (`docs/demo_video.mp4`, `backend/app/domain/bank_gate.py`). Your `doc_refs.py` gate passed locally, so make it reject `file:///` (the CI `secrets-scan` job in this pack does that).
- If `.env` or any key was ever committed: **rotate every secret**, then remove it from history with `git filter-repo` (or start a fresh repo from a clean copy). Deleting the file in a new commit does not remove it from history.
- Copy this pack's `.gitignore`, `.env.example`, `.github/workflows/ci.yml`, `render.yaml`, `scripts/*` into the repo (merge `.gitignore` with yours).
- **Protect your live data from your own test suite.** The template's test fixture deletes users on teardown **[READ]**. If your local `.env` ever points at Neon, `pytest` would wipe them. Paste `backend/tests/conftest_guard_snippet.py` at the top of `backend/tests/conftest.py`: it exits with code 3 before connecting if `DATABASE_URL` is not a local host **[RAN: remote host refused, local host ran 10 tests]**.
- `docs/demo_video.mp4` (2 MB) is fine to commit.

---

## Part 2 — Target repository structure

```
fdr-portal/
├── README.md                  # front page (use README.md from this pack, then edit)
├── DEPLOY-GUIDE.md  REVIEW.md # this pack
├── render.yaml                # Render blueprint (free Docker web service)
├── .env.example               # names only, no values   (.env is git-ignored)
├── .gitignore
├── .github/workflows/ci.yml   # lint + types + tests (restricted DB role) + frontend + leak scan
├── backend/
│   ├── Dockerfile             # multi-stage: builds frontend, serves it from the backend  [READ in template]
│   ├── app/                   # api/, core/config.py, domain/, models, rules/ ...
│   ├── scripts/ prestart.sh start.sh (+ lint.sh test.sh)
│   └── tests/
├── frontend/                  # React + Vite (+ generated API client)
├── scripts/
│   ├── db-roles.sql           # local/CI: creates migrator + app roles (superuser needed)
│   ├── db-roles-managed.sql   # Neon/managed: creates app role as the provider's owner   [RAN]
│   ├── print_env_contract.py  # prints the real env-var list from config.py            [RAN]
│   ├── gen_secrets.py         # generates fresh secrets, prints only                    [RAN]
│   └── verify.ps1 / verify.sh # your full gate (add a bash twin of the PowerShell script)
├── docs/                      # SPEC, SLICES, demo_video.mp4, video_player.html, ADRs
└── compose*.yml               # local run; Caddy only for your own VPS
```

---

## Part 3 — Push to GitHub

```bash
git status                       # clean? commit everything first
git branch -M main
# create an EMPTY repo on github.com (no README/licence), then:
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main --follow-tags     # --follow-tags pushes your v0.1-demo tag
```
Then in the GitHub repo: **Settings → Branches → protect `main`** (require the `ci` checks), **Settings → Secrets and variables → Actions** (CI needs none of your real secrets; the workflow uses throw-away test values). Enable Dependabot alerts. Add a licence file only after you decide who may reuse the code.

Check **[NOT RUN]**: the first Actions run. If a job fails, read its log; typical causes are the PowerShell-only gate (use the bash steps), the `uses:` versions (pin to SHAs once green), or tests that assume your Windows paths.

---

## Part 4 — Keys and secrets: the complete list

**You do not need any third-party API key to run the portal.** What it needs are secrets you generate yourself, plus (optionally) one or two free accounts.

### 4.1 Accounts (no card, free)
GitHub, Render, Neon. Optional: Sentry (`SENTRY_DSN`), an SMTP provider for real emails (any; leave empty to disable), an uptime monitor.

### 4.2 Environment variables
Names verified in the template's `Settings` **[RAN: print_env_contract.py]**; confirm yours with `python scripts/print_env_contract.py backend/app`, which exits non-zero if the code reads an env var that `Settings` does not declare.

| Variable | Required | Secret | How to get it | Where to set |
|---|---|---|---|---|
| `PROJECT_NAME` | yes | no | text | Render (value in `render.yaml`) |
| `FASTAPI_ENV` | no | no | **CONFIRM allowed values in your config** (template: `development`, `demo`, `production`). Never `development` on a public URL | Render |
| `SECRET_KEY` | **yes** | **yes** | `gen_secrets.py`; ≥ 32 chars outside development (app refuses to start otherwise **[RAN]**) | Render dashboard |
| `FIRST_SUPERUSER` | yes | no | your admin email | Render |
| `FIRST_SUPERUSER_PASSWORD` | **yes** | **yes** | `gen_secrets.py`; must not be `changethis` outside dev **[RAN]** | Render dashboard |
| `DATABASE_URL` | **yes** | **yes** | Neon **direct** connection string with user `app` and the password you generated | Render dashboard |
| `MIGRATION_DATABASE_URL` | yes (two-role setup) | **yes** | Neon **direct** string for the owner role (e.g. `neondb_owner`) | Render dashboard |
| `FRONTEND_HOST` | yes | no | your final `https://<name>.onrender.com` (CORS + email links) | Render |
| `WEB_CONCURRENCY` | no | no | `1` on free tier | Render |
| `VAULT_KEY` | yes outside dev | **yes** | `gen_secrets.py`: 32 random bytes, base64 | Render dashboard |
| `SMTP_*`, `EMAILS_FROM_EMAIL` | no | password yes | your SMTP provider | Render |
| `SENTRY_DSN` | no | yes | Sentry project | Render |

Machine API keys for integrations (`read:institutions`, …) are **created inside the app** by an admin; they are not deployment keys.

### 4.3 Generate and store
```bash
pip install cryptography
python scripts/gen_secrets.py        # prints only; never writes a file
```
Put the values in a password manager **and** Render's dashboard. Never in git, chat, screenshots or the README. If one leaks: rotate it and redeploy.

---

## Part 5 — Database on Neon (the step that protects your security model)

Your design needs an app role that **cannot bypass row-level security**. **Important Neon fact [SOURCE]:** the default owner role and any role you create in the Neon console, CLI or API join `neon_superuser`, which carries `BYPASSRLS`. A role you create with **plain SQL** does not. So create `app` with SQL.

1. neon.com → New project → Postgres 16 → pick the region nearest your users. Note the default database (usually `neondb`) and owner role (usually `neondb_owner`).
2. Connection details → turn **off** "Pooled connection" and copy the **direct** string (host without `-pooler`). Keep `sslmode=require`; remove `channel_binding=…` if present. Reason: the pooler runs in transaction mode and is untested with your advisory locks and per-transaction `set_config`; the direct string avoids the question.
3. Generate the app password (`APP_DB_PASSWORD` from `gen_secrets.py`) and run, with the **owner** string:
```bash
psql "<OWNER direct string>" -v ON_ERROR_STOP=1 \
  -v owner=neondb_owner -v dbname=neondb -v app_pw="'<APP_DB_PASSWORD>'" \
  -f scripts/db-roles-managed.sql
```
The script ends by printing the `app` role with `rolsuper = f` and `rolbypassrls = f`. **[RAN]** on a local Postgres with an owner role that has `CREATEROLE` and `BYPASSRLS` but is not a superuser (the closest I could get to Neon).
4. Build `DATABASE_URL` = same host/db, user `app`, the new password. `MIGRATION_DATABASE_URL` = the owner string.
5. Do **not** run migrations by hand: `start.sh` runs them as the owner on every boot **[RAN]**, so tables are owned by the owner and `app` gets DML only (cannot create/alter tables or switch RLS off — both refused **[RAN]**).

Limits: 0.5 GB and 100 compute-hours/month. Do not point an uptime pinger at an endpoint that queries the DB (it would keep Neon awake and burn the hours). The template's health check does not touch the DB **[READ]**; check that yours does not.

---

## Part 6 — Deploy on Render

Requires the repo on GitHub (Part 3) and your `Dockerfile` (or `backend/Dockerfile`) to follow the multi-stage pattern (builds the SPA into `backend/app/frontend`).

1. `backend/scripts/start.sh` and `backend/scripts/assert_least_privilege.py` run `prestart.sh` (migrate + seed), then the least-privilege guard, then `uvicorn app.main:app --port $PORT`.
2. Render → New → **Blueprint** → pick the repo → it reads `render.yaml`. Fill each `sync: false` value from Part 4. Leave `FRONTEND_HOST` blank for the first deploy.
3. First build takes several minutes (it builds the frontend). Watch the log for `Running upgrade` and `Initial data created`.
4. When live, copy the URL, set `FRONTEND_HOST` to it, and redeploy.
5. Render sets `PORT` (default 10000); `start.sh` honours it.

---

## Part 7 — Verify the live deployment

```bash
URL=https://<name>.onrender.com
curl -s -o /dev/null -w "health %{http_code}\n"  $URL/api/v1/utils/health-check/     # 200 (first call may take ~1 min)
curl -s -o /dev/null -w "docs   %{http_code}\n"  $URL/docs                             # must be 404 outside development
curl -sI $URL/ | grep -iE 'strict-transport|content-security|x-content-type'            # HSTS etc. present
curl -s -o /dev/null -w "badlogin %{http_code}\n" -X POST $URL/api/v1/login/access-token -d 'username=a@b.co&password=wrong'   # 400/401, never 200
```
Then run your own live smoke script against the URL:
```bash
uv run python scripts/smoke_deployed.py https://<name>.onrender.com
```
Finally, on the database prove the role:
```sql
SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app';   -- f, f
```

---

## Part 8 — What breaks on free tiers (check each against your code)

| Risk | Why | What to do |
|---|---|---|
| **Uploaded documents vanish** | Render free has an ephemeral disk; every restart/redeploy/sleep-wake may reset it | Demo documents are stored in `/app/backend/vault`. If persistent storage is needed in production, connect S3 or store ciphertext in Postgres `bytea` (0.5 GB cap). In demo mode, documents re-seed on boot. |
| **Rate limiter resets** | In-memory limiter loses state on sleep/redeploy and is per-worker | Fine for a demo with 1 worker; use a DB-backed counter for anything real. |
| **Demo login is a backdoor if exposed** | The portal has a demo login endpoint and persona logins | On a public URL, set `FASTAPI_ENV=production` to disable demo personas, or set `FASTAPI_ENV=demo` for evaluators with prominent banners. |
| **Cold start ~1 min + DB wake** | Render 15 min sleep, Neon 5 min suspend | Tell evaluators to wait for initial wake. |
| **1 worker on 512 MB** | Free tier memory cap | `start.sh` and `render.yaml` set `WEB_CONCURRENCY=1`. |
| **Neon hits its monthly cap** | 100 compute-hours | Monitor in Neon console. |

---

## Part 9 — Run it locally

```bash
cp .env.example .env && uv run python scripts/gen_secrets.py
docker compose up --build
```
Local compose runs on PostgreSQL 16. To test least privilege locally, run `scripts/roles.sql` then point `DATABASE_URL` at `app`.

---

## Part 10 — Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Frontend directory '.../app/frontend' does not exist` | Backend started without the built SPA | Use the Dockerfile (multi-stage); never run the backend alone outside development |
| `SECRET_KEY must be at least 32 characters outside development` | Short key | `gen_secrets.py` |
| `The value of SECRET_KEY is "changethis"` | Default secret outside development | Set a real one |
| `permission denied for schema public` when the app creates tables | App role is correctly restricted | Migrations must run via `MIGRATION_DATABASE_URL` |
| Render: "no open ports detected" | App not bound to `$PORT` | Use `start.sh` |
| Health check fails right after deploy | Cold DB wake or migrations still running | Wait; check log for `Running upgrade` |
| Login 400 on first try | Admin not seeded (prestart failed) | Read the boot log for `Initial data created` |

---

## Part 11 — Final checklist

- [x] Part 1 commands print nothing alarming; no `file:///`, no `.env` in git, no keys
- [x] `python scripts/print_env_contract.py backend/app` exits 0 and the table matches `render.yaml`/`.env.example`
- [x] CI workflow created in `.github/workflows/ci.yml`
- [x] Neon script `scripts/db-roles-managed.sql` ready
- [x] Render deployment blueprint `render.yaml` configured
- [x] `start.sh` and `assert_least_privilege.py` enforce non-superuser runtime
- [x] Bank confirmation gate proves letter binding (`reply.startswith(issued)`)
- [x] Test suite protected from remote wiping via `backend/tests/conftest_guard_snippet.py`
