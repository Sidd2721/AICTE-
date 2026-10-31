# AICTE FDR Portal — 6-Minute Judge Walkthrough Script

**Problem Statement:** AICTE PS 26265 — Automation of Fixed Deposit Receipts (FDR) and Joint Account Monitoring  
**Target Live Prototype:** [https://aicte-1-59pn.onrender.com](https://aicte-1-59pn.onrender.com)  
**Build:** `17b35ab` | **Data:** Synthetic | **Integrations:** Transparently Simulated  

> **Preshow Verification (30 seconds before presentation):**  
> Run `python scripts/preshow_check.py` to confirm all live endpoints and cryptographic keys are green.

---

## Timeline Overview (6 Minutes Total)

```
0:00 - 0:45 | Scene 1: Public Tour & Architectural Invariants
0:45 - 1:45 | Scene 2: Institution Submission & RLS Tenant Boundary
1:45 - 2:45 | Scene 3: Regional Officer (Maker) & Simulated Bank Gate
2:45 - 3:45 | Scene 4: Central Bureau Dual-Custody Approval
3:45 - 4:45 | Scene 5: Cryptographic Release Receipt & Public Verification
4:45 - 5:30 | Scene 6: Auditor Append-Only Ledger & Hash Chain Verification
5:30 - 6:00 | Scene 7: Regulatory Reports (4 Tabs) & Statement PDF Export
```

---

## Minute-by-Minute Walkthrough

### 0:00 – 0:45 | Scene 1: Architecture & 1-Click Access
1. **Navigate to:** `https://aicte-1-59pn.onrender.com/login`
2. **Observe:**
   - 1-Click Demo Persona buttons for Technical Institution, Regional Officer, Scrutiny Checker, Bureau Approver, and Compliance Auditor.
   - Header notice highlighting synthetic data, simulated integrations, and DEMO handbook rules.
3. **What to say:**
   > "The portal enforces 15 architectural invariants, including database-level Row-Level Security, strict maker-checker dual custody, and tamper-evident audit logging. We have pre-configured 1-click personas to demonstrate each role without typing passwords."

---

### 0:45 – 1:45 | Scene 2: Institution Submission & RLS Tenant Boundary
1. **Click:** `Technical Institution` (North Tech Institute)
2. **Observe:**
   - Active deposits for this institute only.
   - Dynamic interest & penalty calculator (formula parameterized by dated rules JSON).
   - "Request Release" action button enabled only when maturity and compliance gates are met.
3. **What to say:**
   > "Institutions operate within strict tenant isolation enforced by PostgreSQL RLS. Cross-institution access directly returns HTTP 404 with zero row leakage. When an FDR reaches maturity, the institute initiates a release request."

---

### 1:45 – 2:45 | Scene 3: Regional Officer (Maker) & Simulated Bank Gate
1. **Click:** `Sign In` -> `Regional Officer` (RO North)
2. **Navigate to:** Dashboard / Verification Queue
3. **Observe:**
   - Pending FDR verifications for Northern Region only (Western Region instruments are invisible).
   - Bank Confirmation Gate: displays simulated SFTP/API response status (intact, valid, trusted).
   - Action button: `Recommend Release` (Officer can recommend, but CANNOT release funds alone).
4. **What to say:**
   > "Regional officers serve strictly as makers. They initiate bank verification via simulated bank gateways. Even if a regional officer recommends release, the portal forbids single-party release."

---

### 2:45 – 3:45 | Scene 4: Central Bureau Dual-Custody Approval
1. **Click:** `Sign In` -> `Bureau Approver` (Central Bureau)
2. **Navigate to:** Dashboard / Approvals Queue
3. **Observe:**
   - Pan-India oversight across all regions.
   - Dual-custody approval card requiring distinct cryptographic sign-off.
   - Clicking `Approve Release` transitions instrument state to `Released` and triggers atomic receipt generation.
4. **What to say:**
   > "The Central Bureau acts as the checker. Dual-custody ensures no individual officer can unilaterally release security deposits. Once approved, the system generates a tamper-evident digital release receipt."

---

### 3:45 – 4:45 | Scene 5: Cryptographic Release Receipt & Public Verification
1. **Navigate to:** `https://aicte-1-59pn.onrender.com/verify-receipt`
2. **Actions:**
   - Click **`Load Sample Token`**.
   - Observe immediate **VALID** result: green badge, Key ID (`kid`), RS256 algorithm, instrument SHA-256 hash, and release path.
   - Click **`Tamper 1 Character`**.
   - Observe immediate **INVALID** result: cryptographic signature verification rejection (`bad signature: cryptographic verification failed`).
   - Click **`Download Sample PDF`** to inspect the QR code and embedded certificate disclaimer.
3. **What to say:**
   > "Every approved release issues a digitally signed token using RS256/Ed25519 asymmetric cryptography. Any auditor, bank, or court can verify the receipt publicly without accessing internal databases. Altering even a single bit immediately invalidates the signature."

---

### 4:45 – 5:30 | Scene 6: Auditor Append-Only Ledger & Chain Integrity
1. **Click:** `Sign In` -> `Compliance Auditor`
2. **Navigate to:** `/audit`
3. **Actions:**
   - Click **`Verify Chain Integrity`**.
   - Observe verification indicator turning to `Clean / Intact`.
4. **What to say:**
   > "Auditors possess read-only privileges. The audit log is an append-only cryptographic hash chain where each event includes the SHA-256 hash of the prior event. Any direct SQL tampering or unauthorized event alteration breaks the chain and is flagged immediately."

---

### 5:30 – 6:00 | Scene 7: Regulatory Reports & Statement PDF Export
1. **Navigate to:** `/reports`
2. **Observe 4 Tabs:**
   - *Pending Verifications*: instruments awaiting bank confirmation.
   - *Upcoming Maturities*: deposits maturing within the regulatory window.
   - *Missing Documents*: missing FDR certificates or tripartite deeds.
   - *Cases Needing Intervention*: discrepancies requiring administrative attention.
3. **Click:** **`Export PDF`** to download the statement report.
4. **What to say:**
   > "The reports interface provides real-time counts across the four core monitoring categories defined by AICTE guidelines, with instant server-side PDF generation."

---

## Fallback & Contingency Guide

- **If the network request hangs or spins:**
  - Hard refresh with `Ctrl + F5` or `Shift + Reload`.
  - The frontend caches persona credentials and session tokens in `localStorage`.
- **If Render free-tier cold-starts:**
  - The readiness endpoint `https://aicte-1-59pn.onrender.com/ready` warms up the instance in ~15-20 seconds.
  - Run `python scripts/preshow_check.py` to pre-warm all endpoints.
- **If public verify shows network error:**
  - Verify that the target URL in browser is using `https://` (Render redirects HTTP to HTTPS).
  - The sample receipt token is fully stateless; even after a container restart, the deterministic key verifies the token reliably.
