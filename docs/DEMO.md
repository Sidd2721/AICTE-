# 7-Step Turnkey Demo Walkthrough — AICTE PS 26265

This walkthrough guides an evaluator through the complete end-to-end capabilities of the AICTE Security Deposit / FDR Portal in 7 reproducible steps.

---

## Prerequisites & One-Command Startup
```bash
# 1. Reset / Seed test matrix
cd backend && uv run python -m app.initial_data

# 2. Run automated validation of the 7 steps
cd backend && uv run pytest tests/test_m9_hardening_and_demo.py -v
```

---

## 7-Step Interactive Walkthrough

### Step 1: Submit an FDR (Institution View)
1. Navigate to `http://localhost:5173/login` and sign in as:
   - **Email:** `inst.north1@example.com` | **Password:** `changethis`
2. Click **Add Deposit** (4-step submission modal):
   - Enter Reference Number: `DEMO-FDR-2026-001`
   - Select Bank: `State Bank of India (SBIN)`
   - Enter Principal Amount: `₹ 15,00,000` (150,000,000 paise)
   - Issue Date: Today | Maturity Date: Today + 10 Years
   - Upload sample PDF/PNG document.
3. Submit and verify deposit appears in *My Deposits* with status **Claimed** (`claimed` badge).

### Step 2: Bank Confirmation & Discrepancy Flagging
1. Sign in as Regional Officer: `officer.north@example.com` | `changethis`.
2. Inspect the submitted deposit in the **Case View**.
3. Trigger Bank Simulator with simulated discrepancy (e.g. Bank confirms only ₹ 10,00,000):
   - System flags **D1_AMOUNT_MISMATCH** in real-time.
   - Status badge transitions to **Changed** / **Discrepancy Open**.
   - Primary action in Needs Action queue updates to *"Resolve Discrepancy"*.

### Step 3: Clock Advance, Obligations & Escalations
1. Advance system clock by 3,620 days (approaching 30-day maturity threshold).
2. Daily worker executes under PostgreSQL advisory lock.
3. Observe:
   - Automated `renewal_due` obligation generated in database.
   - Email reminder notice logged in `notice` table.
   - Needs Action table promotes instrument to high-urgency tier.

### Step 4: Renewal Linking
1. Sign in as Institution user: `inst.north1@example.com`.
2. On expiring instrument, click **Replace / Renew**.
3. Submit replacement FDR `DEMO-FDR-2026-002` for ₹ 15,00,000.
4. Verify:
   - New instrument stores `replaces_id` pointing to old FDR.
   - Old instrument lifecycle transitions from `active` to `renewed`.
   - Complete audit trail preserved across linked lifecycle history.

### Step 5: Fraud Lab Benchmark Inspection
1. Sign in as Bureau Officer: `bureau@example.com` | `changethis`.
2. Navigate to **Fraud Lab & Metrics** page:
   - Review 20 planted discrepancies (D1..D6) + 20 clean instruments.
   - Metrics displayed: **True Positives: 20**, **False Positives: 0**, **False Negatives: 0**, **Accuracy: 100%**.
   - Prominent label: `SYNTHETIC LAB — BENCHMARK VALIDATION ONLY`.

### Step 6: Dual-Custody Release & Offline Receipt Verification
1. On matured clean instrument, Institution user clicks **Request Release** (path: `term_completion`).
2. Regional Officer signs in (`officer.north@example.com`) and verifies checklist -> Status: `verified`.
3. Regional Officer attempts to approve release -> **BLOCKED (HTTP 403: Maker cannot be checker)**.
4. Bureau Officer signs in (`bureau@example.com`) and authorizes release -> Status: `released`.
5. Release receipt token (RS256 JWT) issued.
6. Verify token offline without database:
   ```bash
   cd backend && uv run python -c "from app.domain.receipt import verify_release_receipt; print(verify_release_receipt('<token>'))"
   ```

### Step 7: Bank Outage ("Source Unavailable")
1. Simulate bank gateway disruption via `/sim/bank/simulate-outage`.
2. Portal displays clear, honest status: **"source unavailable" (HTTP 503)**.
3. System safely handles the outage without dropping transactions or showing generic crash errors.

---

**All 7 steps verified and reproducible on demand.**
