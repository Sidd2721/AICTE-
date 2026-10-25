# Secret Scan Report — AICTE PS 26265

**Date:** 2026-10-25  
**Tooling:** Git-aware heuristic pattern analysis + Gitleaks baseline rules  
**Scope:** Full Git history & active workspace files  

---

## Scan Results Summary

| Rule Category | Patterns Tested | Violations Found | Severity | Status |
|---|---|---|---|---|
| **Private Keys (RSA, EC, PKCS8)** | `-----BEGIN (RSA |EC |PRIVATE )KEY-----` | 0 | Critical | **PASS** |
| **API Tokens & JWTs** | `eyJ[A-Za-z0-9_-]{10,}\.eyJ` | 0 in codebase/logs | High | **PASS** |
| **Tracked `.env` Secrets** | `git ls-files --error-unmatch .env` | 0 (strictly untracked) | Critical | **PASS** |
| **Database Credentials** | Hardcoded production database URLs | 0 (injected via environment) | Critical | **PASS** |
| **FDR / Financial Identifiers** | Real PAN, Aadhaar, Live Account Numbers | 0 (strictly synthetic / placeholder) | High | **PASS** |

### Verified Invariants
- **Invariant I12:** Default placeholder secrets (`changethis`) are rejected outside development/demo mode.
- **Invariant I9:** Receipts and audit events carry strictly short hashes of reference numbers without exposing financial or personal details.
- **`.env` Protection:** `.env` is absent from git index, while `.env.example` contains only benign documentation placeholders.
