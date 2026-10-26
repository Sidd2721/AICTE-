# LIMITS — Honest Disclosure of Simulators, Assumptions & Production Path (CHARTER W7)

> **North Star Principle:** "Every fact is claimed or independently confirmed, with method, date and expiry, and the system proves it."
> We explicitly state what is real, what is simulated, and what is required for live government deployment.

---

## 1. What is Real (Engineered & Enforced Today)
| Capability | Reality Status | How to Verify |
| :--- | :--- | :--- |
| **Row-Level Security (RLS)** | **REAL** | PostgreSQL RLS policies enforce regional and institutional isolation at database engine level. |
| **Database Role Isolation** | **REAL** | Runtime `app` role has `NOSUPERUSER` and `NOBYPASSRLS`. Tested in `test_m0_hardening.py`. |
| **Bank Reply Gate** | **REAL in the simulator** | The gate report covers the issued-byte prefix, one signature, validity, trust, whole-file coverage, pinned signer and key usage. Revocation is displayed as not checked in the simulated CA. |
| **Immutable Audit Chain** | **REAL** | Append-only ledger with cryptographic SHA-256 chain hash; verified offline. |
| **Maker-Checker Segregation** | **REAL** | Release requests cannot be approved by the same user who initiated them. Enforced at API & DB level. |
| **Zero Float Arithmetic** | **REAL** | All financial sums stored and calculated strictly as integer paise. |
| **Self-Contained Offline UI** | **REAL** | Zero external CDNs, Google Fonts, or tracking scripts. Verified via `scripts/check-offline.py`. |
| **Single-Worker Footprint** | **REAL** | Stack operates within ~1.5 GB memory footprint with a single backend process. |

---

## 2. What is Simulated (Synthetic Prototype Boundaries)
All simulators are clearly labelled in the user interface and codebase with `[SIMULATED]` badges:

1. **Synthetic Data Only:**
   - All FDR numbers, account numbers, and institution names are synthetic.
   - Real bank names (SBI, HDFC, PNB) and public IFSC prefixes are used solely for realistic routing demonstration.
2. **Bank API / Messaging Channel Simulator:**
    - Candidate production transports include a bank-hosted API or another regulator-approved messaging channel; the choice is open.
   - In this prototype, bank confirmations are generated via an in-process simulator producing genuine PKI-signed PDF responses verified by the real cryptographic gate.
3. **Time Machine Simulator:**
   - Allows evaluators to test time-based lifecycle events (+15 days approaching maturity, +30 days overdue, escalation) without waiting weeks.
   - Reversible clock offset stored in system settings and visible on screen (CHARTER R14).
4. **Email & SMS Notifications:**
   - Captured locally via Mailpit (SMTP port 1025) and mock dispatch logger. No actual SMS or external emails are transmitted.
5. **AICTE Main Portal Integration:**
   - Institution details and application IDs are seeded from synthetic fixtures rather than a live AICTE ERP connection.

---

## 3. What AICTE & Banks Must Provide for Live Production
To move from this validated prototype to national production deployment:

1. **Banking Infrastructure:**
    - API or messaging specifications provided by participating commercial and public sector banks.
   - Pinned root and intermediate CA certificates for authorized bank digital signature tokens.
2. **Regulator Integration:**
   - Integration with AICTE's National Portal / Approval Process Bureau database (SAML 2.0 / OIDC single sign-on).
   - Institutional master registry mapping Permanent Institute IDs to Regional Offices.
3. **Government Hosting & Compliance:**
   - Deployment on NIC (National Informatics Centre) or MeghRaj empanelled cloud infrastructure.
   - Formal security audit and compliance clearance from a CERT-In empanelled auditing firm.
   - Dual-custody HSM (Hardware Security Module) for regulator root key signing.

---

## 4. Open Questions Awaiting AICTE Confirmation
Refer to [docs/OPEN-QUESTIONS.md](docs/OPEN-QUESTIONS.md) for full context:
- Clarification on exact multiplier for leased vs owned private properties (handbook citation: Clause 4.1).
- Delegation of financial powers for release sanctioning (Regional Officer vs Bureau Head threshold limits).
- Auto-renewal mandate conditions under Clause 8.2 when an institution fails to submit renewal within 30 days of maturity.
