# 7-Step Showcase Demo Walkthrough — AICTE PS 26265

This walkthrough guides an evaluator through the complete end-to-end capabilities of the AICTE Security Deposit / FDR Portal in 7 reproducible problem-statement steps matching `scripts/demo_steps.py`.

---

## Prerequisites & One-Command Startup
```powershell
# Reset database cleanly, seed deterministic matrix, and execute all 7 steps:
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset

# Or launch interactive web server (serves compiled SPA on http://localhost:8000):
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1
```

Demo Credentials (all passwords: `changethis`):
- **Institution (North):** `inst.north1@example.com`
- **Regional Officer (North Maker):** `officer.north@example.com`
- **Regional Checker (North Checker):** `checker.north@example.com`
- **Bureau Approver:** `bureau@example.com`
- **Auditor:** `auditor@example.com`
- **System Admin:** `admin@example.com`

---

## The 7 Problem-Statement Demo Steps

### STEP 1: Institution: coverage card -> calculator -> submit FDR
- **Persona:** `inst.north1@example.com` (Institution)
- **UI State:**
  - Navigate to `/deposits`.
  - View the **Coverage Card**: Table 1.4 statutory calculation vs active deposits vs claimed deposits vs remaining shortfall.
  - Interactive Table 1.4 calculator shows required deposit per approved programme.
  - Click **Add Deposit** to submit new FDR (`DEMO-FDR-XXXX`) with State Bank of India, principal ₹ 35,00,000, 10-year term.
  - Badge displays **Claimed** (`claimed` amber badge with explainer popover: "Self-reported by institution; pending independent bank confirmation").
- **Terminal Execution:**
  ```text
  STEP 1: Institution: coverage card -> calculator -> submit FDR - PASSED
  ```

### STEP 2: RO requests bank confirmation -> SIMULATED reply -> gate report
- **Persona:** `officer.north@example.com` (Regional Officer)
- **UI State:**
  - Open `/instruments/$id` (Case View).
  - Side-by-side view shows **Submitted** vs **Confirmed** fields.
  - Trigger bank confirmation inquiry via labelled simulator (`SIMULATED State Bank of India Gateway`).
  - Signed bank reply passes the full 6-point cryptographic gate report (valid digital signature, non-repudiation key usage, byte-prefix continuity, matching trust root).
  - Badge transitions to **Confirmed** (`confirmed` emerald badge).
- **Terminal Execution:**
  ```text
  STEP 2: RO requests bank confirmation -> SIMULATED reply -> gate report - PASSED
  ```

### STEP 3: Break the gate: forged letter / appended page / replayed token
- **Persona:** Evaluator / Security Auditor
- **UI State & Security Verification:**
  - Injects forged PDF confirmation letter not matching AICTE issued challenge -> REJECTED (`not_our_letter`).
  - Injects authentic signed letter with bytes appended after digital signature -> REJECTED (`unreadable_or_invalid`).
  - Injects expired or replayed token -> REJECTED (`token_expired_or_replayed`).
  - Cryptographic gate report renders clear, honest diagnosis of why confirmation failed.
- **Terminal Execution:**
  ```text
  STEP 3: Break the gate: forged letter / appended page / replayed token - PASSED
  ```

### STEP 4: Amount mismatch -> flag with plain message -> waiver demands a reason
- **Persona:** `officer.north@example.com` (Regional Officer)
- **UI State:**
  - Bank confirms ₹ 25,00,000 against claimed ₹ 35,00,000.
  - System automatically flags `D1_AMOUNT_MISMATCH` with human-readable explanation: "Confirmed bank amount is ₹ 10,00,000 less than declared principal".
  - Status transitions to `changed` / `discrepancy`.
  - Officer attempts to waive discrepancy with empty reason -> BLOCKED by schema validation.
  - Submitting formal waiver demands a documented reason and records an append-only audit entry.
- **Terminal Execution:**
  ```text
  STEP 4: Amount mismatch -> flag with plain message -> waiver demands a reason - PASSED
  ```

### STEP 5: Bureau advances the clock 30/60/90 days -> worker -> reminders
- **Persona:** `bureau@example.com` (Bureau Officer)
- **UI State:**
  - Bureau advances system simulated clock by 30, 60, and 90 days.
  - Background worker runs under PostgreSQL advisory locking.
  - Instruments within 60 days of maturity move into the **Expiring** bucket.
  - Matured instruments transition to **Matured** lifecycle.
  - Automated reminder notices dispatched to institution contact log.
- **Terminal Execution:**
  ```text
  STEP 5: Bureau advances the clock 30/60/90 days -> worker -> reminders - PASSED
  ```

### STEP 6: Renewal: replacement FDR -> chain and coverage-gap check
- **Persona:** `inst.north1@example.com` (Institution)
- **UI State:**
  - Institution selects expiring/matured FDR and clicks **Replace / Renew**.
  - Submits replacement instrument with `replaces_id` pointing to the previous FDR.
  - Coverage gap validation verifies the replacement start date and maturity ensure zero gap in AICTE security deposit protection.
  - Case view renders the lineage chain connecting old FDR and replacement FDR.
- **Terminal Execution:**
  ```text
  STEP 6: Renewal: replacement FDR -> chain and coverage-gap check - PASSED
  ```

### STEP 7: Release: institution requests -> RO verifies -> same RO approve blocked -> bureau approves -> receipt -> offline verify
- **Persona:** Institution -> Regional Officer -> Regional Officer (Blocked) -> Bureau Approver
- **UI State:**
  - Institution requests release under `term_completion`.
  - Regional Officer (`officer.north@example.com`) reviews statutory release checklist and clicks **Verify** (`verified_by` recorded).
  - Same Regional Officer attempts to click **Approve** -> **BLOCKED: HTTP 403 Maker cannot be checker**.
  - Bureau Approver (`bureau@example.com`) inspects verified request and clicks **Authorize Release**.
  - System generates signed cryptographic release receipt JWT.
  - Standalone verification script (`scripts/verify_receipt.py`) validates the receipt offline without database or network access.
  - Audit trail at `/audit` displays append-only hash-chained ledger; clicking **Verify Audit Chain** proves chain integrity.
- **Terminal Execution:**
  ```text
  STEP 7: Release: institution requests -> RO verifies -> same RO approve blocked -> bureau approves -> receipt -> offline verify - PASSED
  ```

---

## Resetting Between Demo Runs
To return the environment to a pristine initial state at any time:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset
```
This drops the database, applies all Alembic migrations, re-seeds deterministic credentials and institutions, and verifies all 7 demo steps.
