# VIDEO 2 — COMPLETE SYSTEM ARCHITECTURE WALKTHROUGH & SPECIFICATION
## AICTE Security Deposit & Fixed Deposit Receipt (FDR) Portal
**Problem Statement:** AICTE PS 26265  
**Team:** Sentinel Hubz  
**Target Duration:** 4 minutes 50 seconds (290s) | 90s Judge Cut  
**Format:** Interactive 1080p 60fps Motion Graphics Presentation with Timed Narration & Vector Schematics  
**Artifact Path:** [`docs/video2_architecture_motion_graphics.html`](file:///C:/Users/avadu/26265/docs/video2_architecture_motion_graphics.html)  
**Closed Captions:** [`docs/media/architecture_video.vtt`](file:///C:/Users/avadu/26265/docs/media/architecture_video.vtt)  
**Automation Script:** [`scripts/record_architecture_video.js`](file:///C:/Users/avadu/26265/scripts/record_architecture_video.js)  

---

## 1. Visual Design System & Aesthetics
- **Canvas Resolution:** 1920 × 1080 (16:9 Widescreen High Definition)
- **Primary Color Palette:**
  - Deep Navy Base: `#090d16` to `#0f172a` (radial gradient with subtle 60px matrix grid)
  - Cyan Accent & Glow: `#38bdf8` (`rgba(56, 189, 248, 0.35)`)
  - Institutional Emerald: `#10b981` (Verification Passed, Safe States)
  - Regulatory Amber: `#f59e0b` (Simulated Sandbox Tags, Warning Gates)
  - Authority Indigo / Purple: `#8b5cf6` (Role-Based RLS and Regional Jurisdiction)
  - Crisp Text: `#f8fafc` (Headlines) and `#94a3b8` (Technical Subtitles)
- **Typography:**
  - Headings & Labels: `Segoe UI`, system-ui, -apple-system, sans-serif
  - Monospace Data & Schemas: `Consolas`, `Courier New`, monospace
- **Controls & Interaction:**
  - Interactive Scrubber (00:00 to 04:50) with instant scene jump buttons
  - Real-time Subtitle/Caption display synchronized to milliseconds
  - Web Audio / Speech Synthesis voiceover narrator toggle
  - Live animated SVG and HTML5 Canvas particle data streams

---

## 2. Scene-by-Scene Storyboard & Narration Breakdown

### Scene 1 — Introduction to the Architecture (00:00 – 00:20 | 20s)
- **Visuals:** Complete three-tier system architecture diagram. Left: React 19 Frontend clients (Institution, RO, Bank) entering through Caddy Edge Reverse Proxy. Center: FastAPI application cluster running on Python 3.14 with Deposits Engine, Bank Gateway, and Audit Hash-Chain submodules. Right: PostgreSQL 17 database with RLS and simulated external integrations. Real-time animated canvas showing packet flows across nodes.
- **Narrator Audio:** *"Hello everyone. In this video, I will explain the technical architecture of our AICTE Security Deposit and FDR Verification Portal. We will follow one request through the system to understand how our APIs, database, technologies, data pipelines and routing work together to create a secure and reliable workflow."*
- **Key Technical Callout:** Server-driven workflow architecture with zero floating-point error guarantee.

### Scene 2 — API Architecture: Request Processing & Idempotency (00:20 – 01:10 | 50s)
- **Visuals:** Horizontal request pipeline with 5 interactive stages:
  1. `POST /api/v1/fdr` Client Request
  2. Caddy Edge Proxy (TLS termination, gzip/brotli, rate limiting)
  3. FastAPI Auth & RLS Context Setup (`set_rls_context`)
  4. Pydantic v2 Schema & Business Logic Validation
  5. Server-driven `next_action()` computation and atomic DB commit
- **Code Console Demonstration:** Live FastAPI snippet showing atomic `check_idempotency(db, idempotency_key)` preventing double-submission on network retries.
- **Narrator Audio:** *"First, let's understand the API architecture. Our frontend uses React and TypeScript, while our backend is built with FastAPI and Python. When a user submits an FDR, the request passes through the secure entry point and reaches the appropriate API endpoint. The backend checks the user's identity, validates the incoming data and verifies whether the requested action is allowed. We organize APIs by responsibility: instruments API, deposits API, bank API, release API, and audit API. A key feature is our server-driven workflow: the backend determines the next valid action based on state, permissions, and business rules. Backend idempotency protection ensures network retries never create duplicate deposits or repeat releases."*

### Scene 3 — Database Architecture & Secure Data Storage (01:10 – 01:55 | 45s)
- **Visuals:** PostgreSQL entity web: `institutions`, `fdr_records`, `verification_events`, and `audit_event`. Live demonstration of integer paise representation (`₹35,00,000.00` = `350,000,000 PAISE`). Row-Level Security (RLS) role switcher showing data isolation:
  - College Role: restricted to own institution ID
  - Regional Officer: filtered by regional jurisdiction
  - Statutory Rule: Database-level `CHECK (checker_id != maker_id)` constraint
  - Append-only audit trail with SHA-256 Merkle hash chain
- **Narrator Audio:** *"Next, let's look at the database architecture built on PostgreSQL. Institutions connect to FDR records, and FDR records connect to verification logs and approval workflows. We enforce strict Row-Level Security: colleges only access their own records, regional officers see their jurisdiction, and head office views consolidated national reports. All financial amounts are stored as integer paise to prevent floating-point rounding errors. Role segregation is enforced at the database level: the user who prepares a submission can never approve or release it. Every action is recorded in a cryptographically linked append-only audit trail with SHA-256 hashes for total tamper detection."*

### Scene 4 — Technology Stack & External Integrations (01:55 – 02:35 | 40s)
- **Visuals:** 4-Quadrant tech stack matrix:
  1. Frontend: React 19, TypeScript, Vite 6, TanStack Router, Tailwind CSS, Biome
  2. Backend: FastAPI, Python 3.14, SQLAlchemy 2.0, Alembic, Pydantic v2, uv
  3. Persistence: PostgreSQL 17, RLS, Redis 7 In-Memory, Celery queues, NOSUPERUSER role
  4. Security: SHA-256 Merkle ledger, AES-256 at rest, JWT RS256, DSC signature gate, TLS 1.3
  External integrations status cards: CBS Banking Gateway (Simulated), AICTE Institution Master, DigiLocker / NAD, and Statutory Notification Engine.
- **Narrator Audio:** *"Now let's examine our technology choices and external connections. The frontend is built with React, Vite, and Tailwind CSS. The backend uses FastAPI, Python, SQLAlchemy, and Alembic. PostgreSQL handles data storage while Redis and Celery manage background tasks such as bank verification polling and reminders. For external systems, we integrate with Core Banking Solutions, the AICTE Institution Master Database, and notification services for email and SMS. Security layers protect every connection: JWT tokens, role-based access control, TLS encryption in transit, AES-256 at rest, and digital signature verification."*

### Scene 5 — End-to-End Deposit Lifecycle (02:35 – 03:40 | 65s)
- **Visuals:** 8-Stage animated illuminated circuit board:
  1. FDR Submission
  2. Format & Regulation Validation
  3. Bank Verification Request
  4. Tripartite Agreement & Lien Marking
  5. Active Monitoring & Accrual Engine
  6. Statutory Maturity Alerts (T-90, T-60, T-30 countdown badges)
  7. Release Application & Compliance Certificates
  8. Multi-Tier Maker-Checker DSC Discharge
- **Narrator Audio:** *"Let's follow a deposit through its entire lifecycle across eight automated stages. Stage 1: The college submits deposit details. Stage 2: The system validates bank IFSC, amount against AICTE regulation tables, and required formats. Stage 3: An automated verification request is sent to the bank. Stage 4: The bank confirms lien marked in favor of AICTE, sealing the tripartite agreement. Stage 5: The FDR enters active monitoring with interest tracking. Stage 6: Automated maturity alerts trigger at T-90, T-60, and T-30 days. Stage 7: The college applies for release and uploads necessary compliance certificates. Stage 8: Regional officers review, Finance Bureau validates, and an automated release order is issued with digital signature verification. Every state transition is locked, audited, and mathematically verified without manual paper chasing."*

### Scene 6 — Network Routing & Multi-Role UI Flow (03:40 – 04:20 | 40s)
- **Visuals:** Network topology diagram showing client traffic entering port 443 into Caddy, routing `/api/*` to ASGI port 8000 and static assets to the Vite SPA bundle. 4 live UI screen card previews showcasing College Maker, Bank Officer Verification, Regional Officer Jurisdiction, and National Head Office dashboards.
- **Narrator Audio:** *"Next, let's look at production network routing and interface structure. Client requests enter through Caddy reverse proxy, providing automatic HTTPS, compression, and rate limiting. Requests for the API route to the FastAPI backend, while other requests serve the static React single-page application. Our frontend architecture uses modular route-based structures with TanStack Router, responsive layouts, and accessible components. Real-time updates keep dashboards synchronized across Colleges, Bank Officers, Regional Officers, and National Administrators."*

### Scene 7 — Architecture Summary & Verification Evidence (04:20 – 04:50 | 30s)
- **Visuals:** Four Architectural Pillars:
  1. Scalability (Stateless FastAPI tier + Async DB + Celery background workers)
  2. Security (RLS + Maker-Checker separation + AES-256 + SHA-256 logs)
  3. Reliability (Idempotency keys + Integer paise + Automated retry policies)
  4. Compliance (AICTE APH handbook norms + Tripartite digital liens + DSC release gates)
  Verification Scoreboard featuring real test counts: 192 Backend Tests Pass | 43 Playwright E2E Tests Pass | 7/7 Mutation Proofs Verified Red | 0 Accessibility Violations. Closing credits to Team Sentinel Hubz.
- **Narrator Audio:** *"To summarize, our architecture provides four core advantages: First, Scalability: Stateless APIs and asynchronous task processing handle peak workloads during annual approval cycles. Second, Security: Row-level security, role separation, and cryptographic audit trails protect sensitive financial data. Third, Reliability: Idempotent operations, automated retries, and comprehensive error handling prevent data loss. Fourth, Regulatory Compliance: Strict enforcement of AICTE norms with automated validation and complete auditability. Thank you."*

---

## 3. How to View & Run
1. **Interactive Standalone View (Instant):**  
   Open `docs/video2_architecture_motion_graphics.html` directly in Google Chrome or any modern browser. Press **Play** or scrub to any scene, or enable the **Voice** toggle for real-time speech synthesis.
2. **Recorded 1080p Video:**  
   The video outputs are located at `docs/media/architecture_video_90s_1080p.mp4` (and `docs/media/architecture_video_full_1080p.mp4`).
3. **Automated Re-recording:**  
   Execute:
   ```powershell
   node scripts/record_architecture_video.js preview   # 90-second judge preview
   node scripts/record_architecture_video.js full      # Full 290-second cut
   ```
