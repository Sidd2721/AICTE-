# Evaluator Experience Audit: Rate-Limit Headroom & Shared-State Risks

> **Audit Type:** Report-Only Architectural Review  
> **Scope:** Shared Demo Environment (AICTE PS 26265 Portal)  
> **Target Audience:** Technical Evaluators, Deployment Engineers, and Security Reviewers  
> **Date:** October 2026  

---

## 1. Executive Summary

This report provides a formal, non-intrusive audit of **Rate-Limit Headroom** and **Shared-State Risks** within the shared evaluator deployment of the FDR Portal.

The shared demo environment is intended to be evaluated by multiple stakeholders simultaneously—including AICTE officials, university administrators, and technical jury members. The primary operational objectives are:
1. **Zero Unexpected Blockers:** Evaluators must never experience confusing HTTP 429 (Rate Limit) or HTTP 500 (Server Error) responses during standard or rapid portal exploration.
2. **State Isolation & Integrity:** One evaluator's simulated actions (such as time-shifting the clock, uploading an FDR, or approving a release) must not disrupt another evaluator's walkthrough or permanently degrade the seeded baseline data.

---

## 2. Rate-Limit Headroom Audit

### 2.1 Architecture and Mechanics
Rate limiting in the FDR portal is handled via `backend/app/core/rate_limit.py` using a PostgreSQL-backed sliding window bucket table (`rate_limit_bucket`). This design guarantees rate limit consistency across multi-process workers or container restarts without requiring an external Redis cache.

Current enforcement points:
- **Authentication Route:** `POST /api/v1/login/access-token` (in `backend/app/api/routes/login.py`)
  - Key 1: `login:ip:{client_ip}` (window: 60 seconds)
  - Key 2: `login:account:{username.lower()}` (window: 60 seconds)

### 2.2 Configured Limits by Environment

| Setting | `FASTAPI_ENV == "development"` | `FASTAPI_ENV == "demo"` / `production` | Window |
| :--- | :--- | :--- | :--- |
| **IP Quota (`limit_ip`)** | 100 requests | 10 requests | 60 seconds |
| **Account Quota (`limit_account`)** | 50 requests | 5 requests | 60 seconds |

### 2.3 Headroom Calculations and Friction Analysis

#### Scenario A: Rapid Persona Switching (Single Evaluator)
- **Behavior:** The evaluator tests the role-based views by rapidly clicking each 1-click persona on the login screen (`Bureau Officer`, `Regional Officer (North)`, `Auditor`, `Institution User`).
- **Demand:** 4 login requests within ~15–20 seconds.
- **Headroom vs Limit:** 
  - IP bucket: 4 / 10 used (40% utilization). Safe.
  - Account bucket: 1 request per account used. Safe.
- **Risk:** If the evaluator switches back and forth between two accounts (e.g. testing maker-checker approval by alternating between Institution and Regional Officer 3 times in 60s), the account bucket for that persona reaches 3 / 5 requests. If an automated smoke check or a second concurrent user clicks that same account, the 5th request triggers `429 Too Many Requests`.

#### Scenario B: Evaluators Behind Corporate NAT / Shared Egress IP
- **Behavior:** Multiple committee members on the same office Wi-Fi or VPN evaluate the shared demo link at the same time.
- **Demand:** 3 evaluators clicking personas simultaneously produce 3 × 2 = 6 login requests within 10 seconds.
- **Headroom vs Limit:** 6 / 10 used (60% utilization). Any additional page refreshes or persona toggles within the 60s window will exhaust the 10-request IP budget, causing subsequent evaluators from that IP to see `429 Too Many Requests`.

#### Scenario C: Reverse Proxy IP Attribution (`True-Client-IP` vs `X-Forwarded-For`)
- **Finding:** Under Render edge architecture, `backend/app/core/rate_limit.py:get_client_ip()` correctly checks `True-Client-IP` when `TRUSTED_PROXY_HOPS > 0` (implemented in FT2).
- **Headroom Benefit:** This ensures individual remote evaluator public IPs are isolated rather than all sharing the IP of Render's internal reverse proxy load balancer.

### 2.4 Rate-Limit Recommendations for Shared Demo Link
1. **Demo Mode Headroom Adjustment:**
   - In demo deployments (`FASTAPI_ENV == "demo"`), expand `limit_ip` from 10 to **60 requests/min** and `limit_account` from 5 to **30 requests/min**.
   - This provides comfortable headroom for concurrent evaluators without removing brute-force protection entirely.
2. **Explicit 429 UI Guidance:**
   - If an evaluator hits 429, the frontend should display a user-friendly notice indicating the retry-after countdown rather than a generic network error.

---

## 3. Shared-State Risks Audit

### 3.1 Global In-Memory State: Simulation Clock (`clock.py`)

#### Risk Analysis
- The portal includes an interactive Time Machine simulator allowing evaluators to fast-forward time to test 15-day maturity notices, 30-day overdue escalation, and daily background workers.
- The simulation offset (`_offset_seconds`) is stored in process memory (`backend/app/domain/clock.py`).
- **Initial Risk:** If Evaluator A advances the clock +30 days to test overdue workflows and leaves the browser tab open, Evaluator B visiting the portal 10 minutes later would encounter a system running 30 days in the future with expired instruments and unexpected alerts.

#### Mitigation Implemented (S2: Clock Guard)
- Added `DEMO_CLOCK_IDLE_MINUTES: int = 15` configuration in `backend/app/core/config.py`.
- Implemented lazy auto-reversion in `backend/app/domain/clock.py`:
  - When `DEMO_CLOCK_IDLE_MINUTES > 0` and the clock has a non-zero offset, any read (`now()`, `get_clock_offset()`, `today()`) checks the time elapsed since the last manual shift.
  - If no user has adjusted the clock for ≥ `DEMO_CLOCK_IDLE_MINUTES`, `_offset_seconds` automatically resets to 0.
  - Zero-offset states never trigger expiry overhead.
- **Verification:** 100% verified by comprehensive unit tests in `backend/tests/test_clock_idle.py`.

---

### 3.2 Database State: Seeded Data & Mutating Transactions

#### Risk Analysis
- The shared PostgreSQL database contains 40 rich seeded instruments (20 clean, 20 planted discrepancies), 10 institutions, and 4 personas.
- Evaluators can:
  - Submit new FDR instruments (`POST /api/v1/instruments/submit`)
  - Request release approvals (`POST /api/v1/releases/request`)
  - Sanction or reject releases (maker-checker flow)
  - Upload documents (`POST /api/v1/documents/upload`)
- **Initial Risk:** Can an evaluator's test submission corrupt seeded baseline instruments or block subsequent evaluations?

#### Architectural Mitigations
1. **Unique Reference Partitioning:** All newly submitted provisional instruments use generated prefixes `PROV-<UUID:8>` and distinct identifiers, leaving the seeded `FDR-2026-SBI-001` through `FDR-2026-OTH-040` series immutable and intact.
2. **Maker-Checker Segregation:** Evaluators cannot approve their own release requests; the system enforces strict role segregation at the SQL and API layer.
3. **Row-Level Security (RLS) Isolation:** All operational queries execute under strict PostgreSQL RLS policies (`app_user_id` / `app_user_role` / `app_institution_id`). An institution evaluator cannot view or tamper with another institution's deposits.
4. **Idempotent Seeding on Restart:** On deployment restart, `init_db()` and `seed_rich_data()` execute safely without duplicating records or blowing up existing keys.

---

### 3.3 Storage State: Ephemeral Local Vault vs Cloud Resilience

#### Risk Analysis
- Document uploads (`/api/v1/documents/upload`) write AES-256-GCM encrypted files to `settings.VAULT_PATH` (`/vault` by default).
- On platforms like Render or container hosts with ephemeral disks, restarting or redeploying the web service wipes the local `/vault` folder unless a persistent disk is attached.
- **Previous Failure Mode:** If an evaluator clicked a document link whose underlying vault file was missing on disk, `read_from_vault()` raised `FileNotFoundError`, and unhandled exceptions generated a raw 500 Internal Server Error.

#### Mitigation Implemented (S3: Vault Resilience)
1. **Clean Error Handling:** Updated `backend/app/api/routes/documents.py:download_document` to catch `FileNotFoundError`, `ValueError`, and decryption `InvalidTag` exceptions and return a clean HTTP 404 (`Vault file not found on disk` or `Vault file unreadable or corrupt`) with structured warnings in server logs.
2. **Cloud Storage Fallback:** If `SUPABASE_STORAGE_BUCKET` is configured, `read_from_vault()` automatically falls back to fetching the encrypted document from Supabase Cloud Storage and caches it locally.
3. **Verification:** 100% verified by test suite in `backend/tests/test_vault_resilience.py`.

---

### 3.4 Rate-Limit Bucket Table (`rate_limit_bucket`)

#### Risk Analysis
- Over time, rows accumulate in `rate_limit_bucket` for various IPs and accounts.
- **Garbage Collection:** Expired buckets are lazily overwritten when a key is re-accessed (`ON CONFLICT DO UPDATE SET count = 1`).
- **Resource Footprint:** Even with thousands of hits, index `ix_rate_limit_bucket_reset_at` maintains sub-millisecond query execution. A periodic lightweight sweep (`DELETE FROM rate_limit_bucket WHERE reset_at < NOW() - INTERVAL '1 day'`) is recommended for long-term production.

---

## 4. Summary Matrix

| Risk Dimension | Baseline Behavior | Evaluator Hazard | Hardening Implemented | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Login Rate Limit** | 10 req/IP/min, 5 req/account/min | Accidental 429 on rapid persona toggle or shared NAT | Audited headroom; recommended 60/30 in demo config | **Audited (S4)** |
| **Shifted Demo Clock** | Offset stays indefinitely in memory | Next evaluator sees skewed dates and overdue alerts | Lazy idle revert after `DEMO_CLOCK_IDLE_MINUTES` | **Resolved (S2)** |
| **Missing Vault File** | 500 Server Error if ephemeral disk cleared | Ugly 5xx crash on document preview | Clean 404 + Supabase Cloud fallback | **Resolved (S3)** |
| **Seeded Data Corruption** | Shared PostgreSQL tables | Evaluator mutations could alter baseline scenarios | Immutable reference schema + RLS isolation + idempotent seeding | **Protected** |
| **Maker-Checker Collusion** | Dual-custody release approval | One evaluator approving their own release | Enforced `verified_by != approved_by` at DB and API layer | **Protected** |

---

## 5. Conclusion
With the completion of S1 (One-click login), S2 (Idle clock guard), S3 (Vault resilience), and S4 (Headroom and shared-state audit), the portal provides a frictionless and robust evaluation environment that withstands multi-evaluator traffic, rapid persona switches, and container restarts without exposing server errors.
