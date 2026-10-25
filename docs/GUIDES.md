# User & Role Operational Guides — AICTE PS 26265

Role-based operational guides for the AICTE Security Deposit / FDR Portal prototype.

---

## 1. Institution User Guide (`institution@example.com`)

### Objective: Submit FDRs, track deposit maturity, request replacements and releases.
1. **Sign In:** Use the institutional credentials provided during onboarding.
2. **Deposit Calculator:** Navigate to *Calculator* to compute statutory deposit requirements based on programme, level, leased/owned land, and minority/women exemptions.
3. **Submit New FDR (4 Steps):**
   - Step 1: Enter deposit details (Bank IFSC, Reference Number, Principal in Rupees, Issue Date, Maturity Date).
   - Step 2: Upload joint FDR scan and bank confirmation letter (PDF/PNG magic bytes verified, AES-GCM encrypted in vault).
   - Step 3: Verify institution metadata and confirm AICTE joint lien endorsement.
   - Step 4: Submit to receive instant status (`claimed`) and cryptographic submission receipt.
4. **Renewal / Replacement:**
   - When approaching 90-day maturity alert, click *Replace / Renew* on the deposit details card to link replacement instrument via `replaces_id`.
5. **Request Release:**
   - Once maturity is reached or closure/conversion is approved, submit release request with mandatory checklist items.

---

## 2. Regional Officer Guide (`officer.north@example.com`)

### Objective: Triage Needs Action queue, verify submissions, perform Maker duties.
1. **Needs Action Today Queue:**
   - Displays daily tasks ordered strictly by urgency (matured instruments, open discrepancies, pending verifications).
   - Each row provides 1 primary action button determined deterministically by `next_action()`.
2. **Case Inspection:**
   - Review institution declaration side-by-side with bank confirmation records.
   - Discrepancy flags (D1 Amount, D2 Maturity, D3 Ref, D4 Bank, D5 Lien, D6 Duplicate) appear highlighted with specific variance amounts.
3. **Waiver Management:**
   - If a minor discrepancy is resolved via legitimate annexure or indemnity, record signed waiver reason (audited in ledger).
4. **Maker Verification for Release:**
   - Review release checklist and verify compliance. Clicking *Verify Release* sets status to `verified`.
   - **Dual Custody Invariant:** Regional Officers are prevented from approving releases they verify (`verified_by != approved_by`).

---

## 3. Bureau Approver Guide (`bureau@example.com`)

### Objective: Bureau-level governance, dual-custody Checker sign-off, system-wide metrics.
1. **Checker Release Authorization:**
   - Filter verified release requests. Review Regional verification stamp.
   - Click *Authorize Release* to release instrument and sign RS256 JWT release receipt.
2. **Bureau Analytics & Dashboard:**
   - View real-time counters: Active Deposits, Expiring (30/60/90 days), Matured, Discrepancies Open, Released.
   - Download formula-neutralized CSV compliance reports (`csv_safe`).
3. **Fraud Lab Monitoring:**
   - Inspect synthetic benchmark metrics (TP=20, FP=0, FN=0, Accuracy=100%).

---

## 4. Bank Officer Guide (`sim/bank`)

### Objective: Issue joint lien confirmation, respond to callback requests.
1. **Confirmation Request Receipt:**
   - Banks receive secure confirmation token requests via API callback simulator.
2. **Confirmation Response:**
   - Banks verify reference number, confirmed principal amount, maturity date, and AICTE joint lien marking.
   - Responses signed and validated against 6-point I3 gate (`starter/py/bank_gate.py`).
3. **Outage Behavior:**
   - In the event of bank gateway timeout, system safely labels state *"source unavailable"* (HTTP 503) without corrupting institution records.
