/**
 * Regulatory & Security Glossary (CHARTER G4).
 * Single source of definitions for technical, cryptographic, and governance terms.
 */

export interface GlossaryTerm {
  id: string
  term: string
  plainSummary: string
  detail: string
}

export const GLOSSARY_TERMS: Record<string, GlossaryTerm> = {
  FDR: {
    id: "fdr",
    term: "FDR (Fixed Deposit Receipt)",
    plainSummary:
      "A fixed-term bank deposit held under joint lien for AICTE regulatory approval.",
    detail:
      "A Fixed Deposit Receipt issued by a Scheduled Commercial Bank, pledged jointly with AICTE for a statutory 10-year term as security against institutional obligations.",
  },
  lien: {
    id: "lien",
    term: "Joint Lien Clause",
    plainSummary:
      "A bank restriction preventing the depositor from withdrawing funds without regulator sign-off.",
    detail:
      "A legal encumbrance marked in the Core Banking System (CBS) restricting withdrawal, loan encumbrance, or early closure without express written authorization from AICTE.",
  },
  trust_badge: {
    id: "trust_badge",
    term: "Trust Badge",
    plainSummary:
      "A real-time computed indicator showing whether bank data matches claims.",
    detail:
      "Computed dynamically on every request (never stored in the database): Claimed (institution submitted), Confirmed (bank validated), Stale (needs re-verification), or Changed (tampered post-confirmation).",
  },
  bank_gate: {
    id: "bank_gate",
    term: "Bank Verification Gate",
    plainSummary:
      "A 6-point cryptographic byte-level inspection for authentic bank replies.",
    detail:
      "Full gate check: byte-prefix continuity of the issued challenge letter, exactly one digital signature, unbroken digest, pinned bank root certificate, and non-repudiation key usage.",
  },
  maker_checker: {
    id: "maker_checker",
    term: "Maker-Checker (Dual Custody)",
    plainSummary:
      "Separation of duty: the person who verifies can never approve release.",
    detail:
      "Enforced both in the FastAPI application logic and via PostgreSQL database CHECK constraints (verified_by <> approved_by). No single human can authorize encashment.",
  },
  escalation: {
    id: "escalation",
    term: "Escalation Ladder",
    plainSummary:
      "Automated alerts triggered at T-90, T-60, and T-30 days before maturity.",
    detail:
      "Background worker tracks deposit obligations against dated rule timelines, notifying regional officers and escalating un-renewed deposits to central bureau scrutiny.",
  },
  demo: {
    id: "demo",
    term: "DEMO Values",
    plainSummary:
      "Synthetic and placeholder values for offline product demonstration.",
    detail:
      "Signifies rules, amounts, or configurations taken from draft handbook tables. Startup outside development is blocked until rules are marked CONFIRMED.",
  },
  simulated: {
    id: "simulated",
    term: "SIMULATED Channel",
    plainSummary:
      "A mock bank or email interface that emulates external systems without live wires.",
    detail:
      "No live bank integration is claimed. External banking adapters and SMTP relays run deterministic simulators for reliable and safe evaluation.",
  },
  paise: {
    id: "paise",
    term: "Integer Paise",
    plainSummary:
      "Financial amounts stored strictly in paise (100 paise = ₹1) to avoid rounding errors.",
    detail:
      "Prevents IEEE-754 floating point inaccuracies. All calculations, database columns, and ledger entries use 64-bit integer paise.",
  },
}
