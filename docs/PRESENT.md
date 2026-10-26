# Presentation Pack — AICTE FDR Portal

**Problem Statement PS 26265: Monitoring and Verification of Fixed Deposit Receipts (FDRs)**  
*Prototype for AICTE / Ministry of Education | Synthetic Data & Labelled Simulators Only*

---

## 1. The 30-Second Elevator Pitch

> "AICTE holds security deposit FDRs from technical institutions nationwide, but paper verification is slow and vulnerable to forged bank letters. We built a regulatory portal prototype that checks deposits through the full simulated bank gate, derives requirements from dated Approval Process Handbook rules, enforces dual-custody release authorization, and records actions in a tamper-evident hash chain. In six minutes, we can demonstrate the tested scenarios live."

---

## 2. The 2-Minute Non-Technical Explainer: The Two-Key Locker Analogy

Imagine a high-security bank vault deposit locker:
1. **The Deposit**: When an engineering college opens a new campus, AICTE requires a financial safety net (a fixed deposit pledged jointly to AICTE).
2. **The Problem**: In the past, colleges mailed paper letters claiming their deposit was safe. Forged certificates and prematurely encashed deposits went unnoticed for years.
3. **The Solution (The Dual Keys)**:
    - **Key 1 (The Bank Confirmation)**: The institution cannot simply say "the deposit exists". The labelled bank simulator independently confirms the amount, maturity date, and AICTE lien.
   - **Key 2 (The Dual-Control Release)**: When the 10-year lock-in ends, **no single officer has the key**. The Regional Officer (Maker) verifies compliance, but the system physically blocks them from approving it. A different senior Bureau Head (Checker) must turn the second key.
    - **The Inspection Camera (The Tamper-Evident Ledger)**: Every movement in the room is etched into a cryptographic ledger where each event is hashed to the previous one. External signed checkpoints provide an additional independent reference.

---

## 3. The 6-Minute Live Demonstration Script (Tied to `docs/guide.json`)

| Time | Step | Persona & URL | Key Action to Demonstrate | What to Tell the Evaluators |
| :--- | :--- | :--- | :--- | :--- |
| **0:00 - 0:45** | **1. Rule-Based Calculator** | Institution (`inst@example.com`)<br>`/deposits` | Select programmes & ownership; view Table 1.4 output. | *"Notice zero hardcoded numbers. All deposit obligations derive from dated handbook JSON files in integer paise."* |
| **0:45 - 1:30** | **2. Instrument Submission** | Institution (`inst@example.com`)<br>`/deposits` | Submit an FDR receipt with PDF certificate scan. | *"Submission computes SHA-256 scan hashes immediately. Badge is marked 'Submitted (Claimed)'."* |
| **1:30 - 2:30** | **3. Bank Confirmation Gate** | Regional Officer (`ro@example.com`)<br>`/deposits` | Click 'Trigger Bank Confirmation'. Badge updates to 'Confirmed by Bank (SIMULATED)'. | *"The system queries the bank simulator. Only when all 6 cryptographic gates pass does the Trust Badge turn green."* |
| **2:30 - 3:30** | **4. Discrepancy Defense** | Regional Officer (`ro@example.com`)<br>`/instruments/FDR-B9-301` | Open case with ₹ 10,00,000 discrepancy. Attempt waiver without note (blocked). | *"The bank reports less than claimed. The system halts progress and demands an official scrutiny note before waiver."* |
| **3:30 - 4:30** | **5. Dual-Control Release** | RO -> Bureau Approver<br>`/instruments/FDR-B9-304` | RO verifies release. Try RO approve (blocked 403). Switch to Bureau Head to approve. | *"Maker is never checker (Hard Rule I8). The system enforces separation of duties at the database RLS level."* |
| **4:30 - 5:15** | **6. Break-Me Security Workbench** | Bureau / Evaluator<br>`/instruments/FDR-B9-301` | Inject Replay Attack & Tampered Payload. | *"Watch the full cryptographic gate reject forged signatures and replayed tokens in real time."* |
| **5:15 - 6:00** | **7. Tamper-Evident Audit Ledger** | External Auditor (`auditor@example.com`)<br>`/audit` & `/evidence` | Click 'Verify Chain Integrity'. Review 15 system safety invariants. | *"Every database row is chained via SHA-256. PostgreSQL triggers permanently forbid UPDATE and DELETE."* |

---

## 4. What Each Person Gets

| Persona | Primary Needs & Frustrations | What the Portal Delivers |
| :--- | :--- | :--- |
| **Technical Institution** | Complex handbook calculations; opaque release timelines; lost physical receipts. | Automated Table 1.4 calculator; clear status badges; one-click release requests; cryptographic encashment receipts. |
| **Regional Officer (Maker)** | Sifting through physical bank replies; tracking 10-year maturities; manual spreadsheet logs. | Automated CBS discrepancy alerts; priority action queue; mandatory digital scrutiny notes for audit safety. |
| **AICTE Bureau Head (Checker)** | Fear of rogue releases; lack of cross-regional visibility; regulatory compliance pressure. | Dual-control release approval gate; nationwide compliance dashboard; formula-injection safe CSV exports. |
| **External Auditor / MoE** | Inability to prove records haven't been tampered with; reliance on trust rather than math. | Cryptographically verifiable SHA-256 append-only ledger; formula-safe reporting; 15 provable system invariants. |

---

## 5. Honest Q&A Cheat Sheet (Evaluator Skepticism Responses)

#### Q1: "Are these live bank Core Banking Systems (CBS)?"
**Answer:** *"No. Every bank endpoint in this prototype is a labelled simulator. A live bank API or messaging connection requires written agreements, certificates, transport controls and regulator approval. The simulator exercises the full I3 gate contract."*

#### Q2: "What stops a database administrator from altering a release record?"
**Answer:** *"The ledger is tamper-evident: application roles cannot change it, each row links to the previous hash, and signed checkpoints are stored outside the database. A privileged database operator can still alter database state, so the external checkpoint and verification process are part of the control."*

#### Q3: "What if an officer approves their own release request?"
**Answer:** *"Blocked in code, database, and UI. Invariant I8 specifies `maker != checker`. If `verified_by == current_user.id`, the backend raises an explicit 403 Forbidden with `MAKER_CANNOT_BE_CHECKER`. Parametrized test suites test every permutation."*

#### Q4: "Where are the AICTE handbook deposit rates stored?"
**Answer:** *"In dated, version-controlled JSON files (`deposit.2024-04-01.json`). There is not a single hardcoded monetary constant in the Python or TypeScript codebase. Files marked DEMO block startup outside development."*

---

## 6. Eight-Slide Presentation Structure

- **Slide 1: Title & Mandate** — PS 26265: Automated Monitoring & Verification of Fixed Deposit Receipts.
- **Slide 2: The Core Challenge** — 10-year lock-in durations, paper verification fraud, premature encashment risks.
- **Slide 3: System Architecture** — FastAPI + React 19 SPA, PostgreSQL RLS, CBS Simulator, Append-Only Ledger.
- **Slide 4: Dynamic Handbook Rules Engine** — Table 1.4 programme calculations without hardcoded numbers.
- **Slide 5: Full Cryptographic Bank Gate Report** — Authenticity, signature integrity, coverage, signer pinning, and discrepancy detection.
- **Slide 6: Dual-Custody Maker-Checker Governance** — Hard Rule I8: Institution request -> RO verify -> Bureau approve.
- **Slide 7: Tamper-Evident Ledger & Audit Trail** — SHA-256 hash chaining and immutable PostgreSQL triggers.
- **Slide 8: Proposed Integrations** — AICTE institution directory, bank-hosted API or agreed messaging rail, OIDC identity, and notification gateway; all require agreements.
