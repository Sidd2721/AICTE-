# AICTE Security Deposit / FDR Portal — Live Demo Script

**AICTE PS 26265** | Branch: `sprint/present-anywhere` | Tag: `sprint2-start`

> **IMPORTANT**: All bank and email interactions are **SIMULATED** (transparently labelled).
> All institutions, deposit amounts, and reference numbers are **synthetic**.
> DSC receipts prove document signer, **not bank confirmations**.
> Rule values are marked **DEMO**, pending official handbook confirmation.

---

## Prerequisites

```powershell
# 1. Preflight system health check
uv run python scripts/doctor.py

# 2. Re-seed DB and run all 7 problem statement demo steps:
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset
```

The demo server runs at **http://localhost:8000**.

---

## STEP 1: Institution: coverage card -> calculator -> submit FDR

**Actor:** Institution User (North Tech) (`inst.north1@example.com`)  
**Route:** `/deposits`  
**Goal:** Check mandatory security deposit requirements, calculate required amount, and submit a new fixed deposit record.

### Actions to Perform:
1. Sign in as the Institution persona using the 1-click switcher.
2. Review the Coverage Card showing required versus confirmed deposits.
3. Open the calculator to compute required funds based on selected programmes.
4. Submit a new FDR with reference number, bank code, and 10-year maturity date.

**Expected Outcome:** A new instrument record appears with the Claimed badge, pending bank verification.

**Why this matters:** Institutions can see exact required deposits computed directly from handbook rules without manual guesswork.

---

## STEP 2: RO requests bank confirmation -> SIMULATED reply -> gate report

**Actor:** Regional Officer (North Region) (`officer.north@example.com`)  
**Route:** `/deposits`  
**Goal:** Request authoritative bank verification for a submitted deposit and inspect the cryptographic validation report.

### Actions to Perform:
1. Switch to the Regional Officer persona.
2. Open the case page for the submitted instrument.
3. Click the single primary action button 'Request Bank Confirmation'.
4. View the full cryptographic verification gate report.

**Expected Outcome:** The enforced checks pass; simulated revocation is shown as not checked and the status badge turns green to Confirmed (SIMULATED).

**Why this matters:** No deposit is trusted on institution claims alone. Bank verification confirms validity cryptographically.

---

## STEP 3: Break the gate: forged letter / appended page / replayed token

**Actor:** Regional Officer (North Region) (`officer.north@example.com`)  
**Route:** `/deposits`  
**Goal:** Test system defenses by attempting three common fraud attacks against the bank verification gate.

### Actions to Perform:
1. In the Break-Me Workbench on the case page, select 'Forged Letter Attack'.
2. Test an 'Appended Bytes' attack where trailing pages were added.
3. Test a 'Replayed Token' attack using an already consumed verification challenge.

**Expected Outcome:** Every attack is immediately rejected with clear explanations and zero false passes.

**Why this matters:** Standard PDF signers often miss appended pages. The portal enforces byte-prefix and boundary checks.

---

## STEP 4: Amount mismatch -> flag with plain message -> waiver demands a reason

**Actor:** Regional Officer (North Region) (`officer.north@example.com`)  
**Route:** `/deposits`  
**Goal:** Detect an amount discrepancy between bank and institution claims and enforce accountability before waiver.

### Actions to Perform:
1. Run an amount mismatch test where the bank confirms less than claimed.
2. Notice the plain-language warning explaining the shortfall.
3. Try waiving the flag with a blank reason to confirm validation blocks it.
4. Enter a detailed reason of at least 10 characters to record the waiver.

**Expected Outcome:** The waiver is accepted only with a written justification and permanently logged to audit.

**Why this matters:** Officers cannot silently bypass discrepancies without creating an immutable paper trail.

---

## STEP 5: Bureau advances the clock through rule offsets -> worker -> reminders

**Actor:** Bureau Approver (Central) (`bureau@example.com`)  
**Route:** `/dashboard`  
**Goal:** Fast-forward the virtual clock to test automated background reminders and escalation notices.

### Actions to Perform:
1. Switch to the Bureau Approver persona.
2. Open the Time Machine dropdown in the header and advance +30 days.
3. Advance to +60 days to trigger escalation notices.
4. Advance to +90 days to verify overdue alerts and review emails in Mailpit.

**Expected Outcome:** Dashboard categories automatically update and reminder emails appear without manual tracking.

**Why this matters:** Automates tracking for 10-year deposits so renewals and maturities are never forgotten.

---

## STEP 6: Renewal: replacement FDR -> chain and coverage-gap check

**Actor:** Institution User (North Tech) (`inst.north1@example.com`)  
**Route:** `/deposits`  
**Goal:** Submit a replacement FDR linked to an expiring instrument and verify custody continuity.

### Actions to Perform:
1. Switch back to Institution persona.
2. Submit a renewal FDR referencing the original instrument ID.
3. Open the case page to review the linked predecessor.
4. Check that coverage continuity is maintained without unmonitored gaps.

**Expected Outcome:** The old instrument links to the new one in a complete verifiable renewal chain.

**Why this matters:** Prevents institutions from letting deposits lapse during renewal transitions.

---

## STEP 7: Release: institution requests -> RO verifies -> same RO approve blocked -> bureau approves -> receipt -> offline verify

**Actor:** Institution & Bureau Personas (`bureau@example.com`)  
**Route:** `/deposits`  
**Goal:** Perform dual-custody authorized deposit release and verify cryptographic encashment receipt.

### Actions to Perform:
1. As Institution, request term completion release.
2. As Regional Officer, verify the request (maker step).
3. Confirm that Regional Officer cannot approve (role check blocks it).
4. As Bureau Approver (checker), approve release and view cryptographic receipt.

**Expected Outcome:** Status becomes Released, receipt token is generated, and audit chain passes verification.

**Why this matters:** No single officer can authorize the release of security deposits. Dual-custody stops insider fraud.

---

## Demo Credentials Matrix

| Persona Role | Email | Region | Permission Scope | Password |
| :--- | :--- | :--- | :--- | :--- |
| **Institution** | `inst.north1@example.com` | NR | Submits FDR, requests release | `changethis` |
| **Regional Officer** | `officer.north@example.com` | NR | Requests bank confirmation, verifies release | `changethis` |
| **Regional Checker** | `checker.north@example.com` | NR | Regional inspection & notes | `changethis` |
| **Bureau Head** | `bureau@example.com` | ALL | Approves release (checker), all reports | `changethis` |
| **Auditor** | `auditor@example.com` | ALL | Read-only audit log & instruments | `changethis` |

*(All demo personas are accessible via 1-click login buttons on `/login` and `/guide`)*
