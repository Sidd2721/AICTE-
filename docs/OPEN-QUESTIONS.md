# OPEN-QUESTIONS.md — FDR Portal (AICTE PS 26265)

Unresolved items that block finalising rule data or implementation decisions.
Never guess handbook numbers — add them here and mark them as PLACEHOLDER in rule files.
Format: `OQ-NNN | Slice | Status | Question | Source hint`

---

## Rulebook (Section 3 of BRIEF.md)

| ID     | Slice | Status      | Question                                                                                                          | Source hint                                      |
|--------|-------|-------------|-------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| OQ-001 | M2    | OPEN        | Late-proof penalty percentages and cut-off dates: 10%/20% vs 10%/50% with 30 May / 31 July cuts — which is correct? | Two copies of the handbook disagree               |
| OQ-002 | M6    | OPEN        | Release penalty in the six-years-not-applied closure case: 10% or 50%?                                           | Copies disagree                                  |
| OQ-003 | M6    | OPEN        | "Balance amount" top-up computation and remaining-term logic                                                       | Handbook unclear                                 |
| OQ-004 | M6    | OPEN        | Competent authority per release path; does grievance/vigilance clearance apply to all paths?                      | Not stated clearly in available sources           |
| OQ-005 | M4    | OPEN        | Acceptable banks and instrument types (which banks are on the approved list?)                                     | AICTE circular not obtained                       |
| OQ-006 | M4/M8 | OPEN       | How are RTGS/online deposits held and paid back?                                                                  | No operational guidance obtained                  |
| OQ-007 | M5    | OPEN        | Escalation ladder (who escalates to whom, at what intervals?)                                                     | Not in handbook                                  |
| OQ-008 | M5    | OPEN        | Alert offsets — are 30/15/7/1 days before maturity the correct defaults?                                          | Assumed; confirm with AICTE                       |
| OQ-009 | M1/M9 | OPEN       | Retention periods for audit events, documents and personal data                                                   | DPDP rules pending; AICTE policy not seen         |
| OQ-010 | M1    | OPEN        | AICTE institution identifier format (for AICTE ID field in institution table)                                     | Not confirmed from official source                |
| OQ-011 | M9    | OPEN        | National Single Window hand-off — required? What protocol?                                                        | Mentioned in brief; not specified                 |
| OQ-012 | M9    | OPEN        | Hosting domain and DPDP applicability to this system specifically                                                 | Legal question; needs lawyer sign-off             |
| OQ-013 | M4    | OPEN        | CCA trust roots for DSC verification — which bundle to use?                                                       | Controller of Certifying Authorities              |
| OQ-014 | M4    | OPEN        | Affidavit 4 = closure — not confirmed from the 2024-27 official PDF                                               | [OPEN] per BRIEF-PATCHES.md item A.5             |
| OQ-015 | M2    | OPEN        | 2026-27 handbook addendum — does it change the deposit table or its scope?                                        | News report only; SINGLE source; verify           |
| OQ-016 | M4    | OPEN        | Bank re-saves PDF before signing — does the I3 gate's byte-prefix check reject genuine replies?                   | BRIEF-PATCHES.md P-8; keep manual-review path    |
| OQ-017 | M3    | OPEN        | Does AICTE accept unsigned document uploads for instrument submission?                                            | BRIEF-PATCHES.md P-7; decision: accept but flag  |
| OQ-018 | M4    | OPEN        | Regional officer NOC — is it required for release, and under which paths?                                         | BRIEF-PATCHES.md; COPY source only               |
| OQ-019 | M1    | OPEN        | Which rate-limit library to use for login throttling? (Template has none)                                         | Ask before adding dependency                      |
| OQ-020 | M3    | OPEN        | PDF library for confirmation letter generation — is `reportlab` acceptable or use another?                        | Ask before adding dependency                      |

## Infrastructure / Deployment

| ID     | Slice | Status      | Question                                                                                                          |
| OQ-021 | M0    | RESOLVED    | PostgreSQL version decision: Resolved via D-07 -> pin to 16 (`postgres:16`)                                       |
| OQ-022 | M9    | OPEN        | Production hosting environment and domain name                                                                    |
| OQ-023 | M9    | OPEN        | CERT-In or STQC-empanelled security audit — has engagement started?                                              |
| OQ-024 | M9    | OPEN        | Legal review of data-protection obligations — has engagement started?                                            |

---
_Last updated: 2026-10-25. Add new questions here; never guess; never hardcode unconfirmed numbers._
