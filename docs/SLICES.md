# Slices & Milestones Roadmap — AICTE PS 26265

The system is delivered in thin, verifiable slices (M0 through M9) strictly in sequential order.

| Slice | Name | Scope & Core Deliverables | Done-When Criteria |
|---|---|---|---|
| **M0** | **Harden Template** | Purge sample items, delete signup route, 60-min tokens, untrack `.env`, PostgreSQL 16 pinned, initial seed users. | Baseline test suite passing, full gate passes, fresh DB builds cleanly from migrations. |
| **M1** | **Schema, Access, Audit** | 12 SQLModel tables, RLS policies, audit hash-chain (`audit_append`), RLS context helper, rate limiting. | Ported 26 DB behavior checks pass, RLS leaks 0 rows on missing context, `audit_verify()` returns NULL. |
| **M2** | **Rules & Calculator** | Dated rulebook, startup guard, dev clock service, deposit calculator summing programmes & multipliers. | Startup refuses DEMO in production, owned vs leased calculations match Table 1.4, exempts government. |
| **M3** | **Submission & Vault** | 4-step institution submission flow, magic-bytes upload check, SHA-256 deduplication, AES-GCM encryption with AAD. | Disguised files rejected (415), same file 409, cross-record decryption fails, badge is "claimed". |
| **M4** | **Bank Gate & Discrepancies** | Bank simulator, issued letter PDF, 6-point I3 gate, D1–D6 discrepancy checks, waiver flow, officer Case view. | 10 bank gate attack cases pass, D1..D6 positive & negative tests pass, officer advances case to active. |
| **M5** | **Obligations & Worker** | Obligations lifecycle, background daily worker with advisory lock, automated reminder offsets, renewal gap (D7). | Advisory lock prevents double execution, clock +30d sends 1 reminder, renewal gap raises D7. |
| **M6** | **Authorised Release** | 4 release paths (term completion, closure, merger, conversion), dual-custody maker-checker, signed PyJWT receipt. | `verified_by == approved_by` blocked, bureau-only approval, receipt tampering fails, offline script verifies. |
| **M7** | **Dashboard & Reports** | 6 counters via `dashboard_bucket`, Needs Action queue, full-text search, 4 CSV reports with `csv_safe`. | Counters update upon state changes, CSV formula injection neutralised, search is scoped by RLS. |
| **M8** | **Fraud Lab & E2E Scenarios** | 20 planted discrepancies, 20 clean instruments, accessibility pass, 6 statement end-to-end scenarios. | 6 automated Playwright scenarios pass, TP=20, FP=0, FN=0 reported, timing comparison sheet complete. |
| **M9** | **Hardening & Demo Run** | Security headers, structured JSON logs, dependency/secret scan reports, 7-step demo walkthrough script. | Production refuses default secrets/DEMO rules, demo script runs twice from clean setup without errors. |
