# AICTE Security Deposit / FDR Portal — Live Demo Script

**SIH PS 26265** | Branch: `sprint/mvp-showcase` | Tag: `mvp-showcase`

> **IMPORTANT**: All bank and email interactions are **SIMULATED** (transparently labelled). All institutions, deposit amounts, and reference numbers are **synthetic**. DSC receipts are unsigned test certificates, **not bank confirmations**. Rule values are marked **DEMO**, pending official handbook confirmation.

---

## Prerequisites

```powershell
# 1. Preflight checks
uv run python scripts/doctor.py

# 2. Reset DB, run migrations, seed, launch server, and execute all 7 steps:
powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset
```

The demo server runs at **http://localhost:8000**. Default credentials are printed by `doctor.py`.

---

## STEP 1: Institution: coverage card -> calculator -> submit FDR

**Actor:** Institution user (`inst.north1@example.com`)
**Route:** `/` -> `/deposits` -> submit form

1. Log in using the **1-click demo personas** on the login page.
2. The dashboard shows the **Coverage Card**: Required (Table 1.4 APH) vs Confirmed-Active vs Claimed-Only vs Shortfall.
3. Open the **coverage calculator**: programme type, intake, land ownership. Required deposit is computed from the dated rule JSON - no hand-typed values.
4. Click **Submit FDR**. Status badge shows: **"Submitted by institution (not bank-confirmed)"**

---

## STEP 2: RO requests bank confirmation -> SIMULATED reply -> gate report

**Actor:** Regional Officer (`officer.north@example.com`)
**Route:** `/instruments/<id>` Case page

1. Open the instrument from Step 1.
2. Click **"Request Bank Confirmation"** (primary button from `next_action()`).
3. The SIMULATED bank simulator responds. The system runs the full gate (`check_bank_reply`): integrity hash, signature chain, duplicate-reply guard.
4. Status badge: **"Confirmed by bank (SIMULATED)"**

---

## STEP 3: Break the gate: forged letter / appended page / replayed token

Three attacks, each rejected with its specific reason:

| Attack | Rejection |
|--------|-----------|
| Forged letter | `INTEGRITY_FAIL: Document hash does not match signed value` |
| Appended page | `INTEGRITY_FAIL: Content hash mismatch after byte-level verification` |
| Replayed token | `REPLAY_REJECTED: Bank reference already confirmed for this instrument` |

---

## STEP 4: Amount mismatch -> flag with plain message -> waiver demands a reason

1. Bank confirms a different amount than institution claimed.
2. System raises a **DISCREPANCY flag** with plain message from `lib/messages.ts`.
3. RO must enter a **mandatory written reason** to waive. Blank reason = HTTP 422.
4. Waiver is logged to the immutable audit ledger.

---

## STEP 5: Bureau advances the clock 30/60/90 days -> worker -> reminders, escalation, needs-action reorders, mail in Mailpit

1. Bureau user advances the virtual clock by 30 days -> worker runs -> **Needs Action** panel reorders.
2. 60 days total -> ESCALATED status appears. Reminder email in Mailpit (`http://localhost:8025`).
3. 90 days total -> OVERDUE. Escalation emails dispatched.

> Thresholds (30/60/90) are read from `rules/timelines.json`, not hardcoded.

---

## STEP 6: Renewal: replacement FDR -> chain and coverage-gap check

1. Submit a new FDR referencing the expiring FDR as predecessor.
2. System validates: renewal chain validity + coverage-gap check.
3. Case page shows **"Renewal chain"** link to predecessor.

---

## STEP 7: Release: institution requests -> RO verifies -> same RO approve blocked -> bureau approves -> receipt -> offline verify -> /audit Verify chain -> /evidence

| Sub-step | Actor | Action | Result |
|----------|-------|--------|--------|
| 7a | Institution | Request Release | Status: RELEASE_REQUESTED |
| 7b | RO (maker) | Verify Release | Status: RELEASE_VERIFIED |
| 7c | Same RO (checker) | Try Approve | **BLOCKED: "The same person cannot both verify and approve"** |
| 7d | Bureau (checker) | Approve Release | Status: RELEASED, receipt generated |
| 7e | Anyone | Verify offline | `python scripts/verify_receipt.py receipt.json` -> VALID |
| 7f | Auditor | Audit Verify Chain | `/audit` -> OK — N events hash-chain-intact |
| 7g | Anyone | Evidence dashboard | `/evidence` -> 10/10 caps, 29/29 tests |

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Institution | inst.north1@example.com | changethis |
| Regional Officer (Maker) | officer.north@example.com | changethis |
| Regional Officer (Checker — blocked) | checker.north@example.com | changethis |
| Bureau | bureau@example.com | changethis |
| Auditor (read-only) | auditor@example.com | changethis |

---

## What This Demo Does NOT Claim

- No real bank verification (SIMULATED, transparently labelled)
- Not WCAG-audited, not production-hardened, not certified
- No real monetary flows (synthetic data only)
- DSC receipts are unsigned test certificates, not bank confirmations
- Fraud-lab numbers are labelled-synthetic
- TIMING baseline is estimated, not measured in production
- Rule values are DEMO-flagged, pending official handbook confirmation
