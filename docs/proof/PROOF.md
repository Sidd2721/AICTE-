# AICTE FDR Portal — Live Verification Proof Pack

- **Target Deployment**: [https://aicte-1-59pn.onrender.com](https://aicte-1-59pn.onrender.com)
- **Deployment Build SHA**: `17b35ab` (Matches `main` branch HEAD)
- **Verification Date**: 2026-10-31
- **Status**: 12/12 Live Verification Checks Passed (0 Errors, 0 Unintended 4xx/5xx)

> **Regulatory Prototype Disclaimer**:
> This software is an engineering prototype for AICTE Problem Statement 26265. All institution names, deposit amounts, reference numbers, and financial records are **synthetic**. Bank gateway integrations (SFTP, API, webhook callbacks) and email dispatch mechanisms are **simulated** with transparent audit labelling. Release receipt PDFs are non-negotiable prototype records and **not bank instruments; no funds are released**.

---

## 1. Verified Proof Artifacts

All screenshots were captured live against `https://aicte-1-59pn.onrender.com` using Playwright in headless Chromium (`1280x800` viewport, `1x` scale). Total size across all 9 screenshots is **1.23 MB** (strictly adhering to the 3.00 MB limit).

| # | Artifact File | Caption | Purpose / Verified Claim | File Size |
|---|---|---|---|---|
| 1 | [`01_login_page.png`](01_login_page.png) | Sign In & 1-Click Demo Personas | Demonstrates 1-click persona logins, role badges, and zero password typing for demo workflows. | 73.8 KB |
| 2 | [`02_institution_dashboard.png`](02_institution_dashboard.png) | Technical Institution Dashboard | Shows tenant-isolated view of active deposits, penalty calculator, and submission controls. | 199.0 KB |
| 3 | [`03_regional_officer_queue.png`](03_regional_officer_queue.png) | Regional Officer (Maker) Queue | Displays regional queue, verification triggers, and bank confirmation initiation. | 229.8 KB |
| 4 | [`04_bureau_overview.png`](04_bureau_overview.png) | Central Bureau Approver Overview | Dual-custody approval queue; proves maker is never checker; bureau sign-off authority. | 202.4 KB |
| 5 | [`05_auditor_ledger_verified.png`](05_auditor_ledger_verified.png) | Cryptographic Audit Ledger Verification | Read-only auditor interface showing append-only SHA-256 event chain with "clean" integrity badge. | 73.2 KB |
| 6 | [`06_reports_tabs.png`](06_reports_tabs.png) | Statement Reports (4 Regulatory Tabs) | Shows all 4 mandatory tabs: Pending Verifications, Upcoming Maturities, Missing Docs, Intervention Cases. | 119.0 KB |
| 7 | [`07_sample_receipt.png`](07_sample_receipt.png) | Demo Release Receipt PDF Preview | Rendered sample receipt with QR code, RS256 digital signature token, SHA-256 instrument hash. | 134.0 KB |
| 8 | [`08_verify_receipt_valid.png`](08_verify_receipt_valid.png) | Public Receipt Verifier: VALID | Public independent verification showing green shield, verified key ID, RS256 algorithm, and claims. | 122.9 KB |
| 9 | [`09_verify_receipt_invalid.png`](09_verify_receipt_invalid.png) | Public Receipt Verifier: INVALID | Immediate cryptographic rejection when a single character of the signature token is tampered. | 105.2 KB |

**Total Screenshot Bundle Size**: **1.23 MB** (< 3.00 MB threshold).

---

## 2. Live Verification Suite Results (`verify_live.py`)

Run against live target `https://aicte-1-59pn.onrender.com`:

```text
================================================================================
AICTE FDR Portal — Live Verification Suite
Target: https://aicte-1-59pn.onrender.com
================================================================================
[PASS] 1. Readiness Probe (/ready) — HTTP 200, build=17b35ab (0.18s)
[PASS] 2. Unauthenticated Access Defense (/api/v1/instruments/) — HTTP 401 (Expected 401/403)
[PASS] 3. Five Persona Logins — Acquired JWT tokens for all 5 personas
[PASS] 4. Tenant and Regional Isolation (RLS Scope Defense) — NR=25, WR=11, overlap=0, cross-fetch=404 (expected 404)
[PASS] 5. Statement Reports (4 Tabs Preview) — pending-verifications: 10; upcoming-maturities: 10; missing-documents: 18; cases-needing-intervention: 5
[PASS] 6. Statement PDF Export (/api/v1/reports/pdf) — HTTP 200, is_pdf=True, size=38569 bytes (0.99s)
[PASS] 7. Demo Sample Receipt PDF (/api/v1/demo/sample-receipt.pdf) — HTTP 200, is_pdf=True, size=172406 bytes (< 300KB: True)
[PASS] 8. Sample Receipt Token Verification (/api/v1/receipts/verify) — HTTP 200, valid=True, claims=['receipt_id', 'iat', 'instrument_hash', 'path', 'kid', 'release_id'], reason=None
[PASS] 9. Tampered Receipt Token Rejection (/api/v1/receipts/verify) — HTTP 200, valid=False, reason='bad signature: cryptographic verification failed'
[PASS] 10. Public Verify SPA Route (/verify-receipt) — HTTP 200, has_html=True (0.12s)
[PASS] 11. API Documentation Status (/docs) — HTTP 404 (Locked 404)
[PASS] 12. Security Headers (CSP, nosniff, DENY) — nosniff=True, xframe=True, csp=True
================================================================================
VERIFICATION SUMMARY: 12/12 CHECKS PASSED
================================================================================
```

---

## 3. Pre-Show Quick Check Results (`preshow_check.py`)

Fast, read-only sanity check executed prior to presentations:

```text
Running Pre-show Health Check against: https://aicte-1-59pn.onrender.com

  [PASS] 1. Readiness Probe (/ready) (HTTP 200, build=17b35ab)
  [PASS] 2. Unauthenticated Access Defense (/api/v1/instruments/) (HTTP 401)
  [PASS] 3. Public Verify Route (/verify-receipt) (HTTP 200)
  [PASS] 4. Demo Sample Receipt PDF (/api/v1/demo/sample-receipt.pdf) (HTTP 200, size=172406 bytes)
  [PASS] 5. Sample Token Verification (/api/v1/receipts/verify) (valid=True)
  [PASS] 6. Tampered Token Rejection (rejected bad signature)
  [PASS] 7. Security Headers (CSP, nosniff, DENY) (csp=True, nosniff=True, xframe=True)

==================================================
Preshow Summary: 7/7 checks passed
==================================================
```

---

## 4. Key Security & Architectural Properties Verified

1. **Cryptographic Release Verification**: Receipts are signed via RS256/Ed25519 asymmetric keys. Independent third parties verify receipts without database or network access to private data.
2. **Row-Level Security (RLS)**: PostgreSQL enforces tenant isolation directly in SQL engine; cross-institution/region access returns 404 with 0 rows leaked.
3. **Dual-Custody Enforcement**: Regional officers can only verify/recommend release; Central Bureau must separately approve. The system strictly prevents maker from acting as checker.
4. **Tamper-Evident SHA-256 Audit Chain**: Every critical event is chained to previous events. Modifying any past event invalidates the hash chain integrity.
