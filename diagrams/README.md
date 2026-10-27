# AICTE FDR Portal — Architecture & Feature Component Diagrams (PS 26265)

This directory hosts the comprehensive architectural and feature diagrams for the **AICTE Fixed Deposit Receipt (FDR) & Security Deposit Regulatory Portal**.

> **Master Specification**: See the full workable diagram document at [`docs/DIAGRAMS.md`](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md).

---

## Quick Reference Index of Diagrams

1. **[Master C4 Topology & Architecture Diagram](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#1-master-system-architecture--c4-topology-diagram)**:
   Five concentric tiers (Ingress, API Runtime, Core Cryptographic Engines, Asynchronous Outbox Pipelines, and PostgreSQL 16 RLS Storage).

2. **[Document Vault Ingestion Pipeline](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#2-feature-1-document-vault-ingestion--magic-byte-encryption-pipeline)**:
   Magic byte sniffing (`%PDF-1.4`), SHA-256 digest computation, and AES-256-GCM envelope encryption with instrument-scoped Additional Authenticated Data (AAD).

3. **[6-Point Cryptographic Bank Gate](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#3-feature-2-6-point-cryptographic-bank-gate--digital-signature-verification)**:
   Deep inspection: Header Prefix, Signature Authenticity, Entire-File Byte Coverage (`SignatureCoverageLevel.ENTIRE_FILE`), Digest Integrity, CCA Root Anchor, Non-Repudiation Key Usage (IT Act 2000 Section 3A), and Anti-Replay Nonces.

4. **[Regulatory Scrutiny & Discrepancy Triaging Engine](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#4-feature-3-dynamic-regulatory-scrutiny--discrepancy-triaging-engine)**:
   Dynamic Table 1.4 rules matrix evaluation without hardcoded numbers; checks D1 to D6 (Amount, Tenure, Ref, Bank, Lien, Duplicate).

5. **[Dual-Custody Release Governance (Maker-Checker)](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#5-feature-4-dual-custody-separation-of-duties-release-engine-maker-checker)**:
   Database-level constraint `chk_release_request_maker_checker (verified_by != approved_by)` guaranteeing that no single officer can release multi-crore student safety funds.

6. **[Immutable Append-Only Audit Ledger](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#6-feature-5-append-only-cryptographic-audit-ledger--continuity-verification)**:
   Mathematical SHA-256 hash chaining ($\text{entry\_hash} = \text{SHA256}(\text{prev\_hash} + \dots)$) with procedural database triggers forbidding `UPDATE`, `DELETE`, and `TRUNCATE`.

7. **[Multi-Tenant Row-Level Security (RLS) Pipeline](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#7-feature-6-multi-tenant-row-level-security-rls-isolation-pipeline)**:
   PostgreSQL kernel-level isolation across all 8 AICTE regions with `NOSUPERUSER` and `NOBYPASSRLS` runtime credentials.

8. **[Asynchronous Maturity Radar & Obligation Worker](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#8-feature-7-proactive-maturity-radar--automated-obligation-lifecycle-worker)**:
   Daily automated scanning of `instrument_maturity_idx` under advisory lock `847291`, firing proactive alerts at T-90, T-60, and T-30 days before maturity.

9. **[Scrutiny Discrepancy Waiver State Machine](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#9-feature-8-scrutiny-discrepancy-waiver-governance-state-machine)**:
   Structured waiver lifecycle requiring $\ge 10$-character audit justification before any discrepancy can be resolved.

10. **[Transactional Outbox & Resilient Webhook Engine](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#10-feature-9-transactional-outbox--resilient-webhook-dispatcher)**:
    Decoupled event streaming using `SELECT FOR UPDATE SKIP LOCKED` and HMAC-SHA256 signature verification.

11. **[Multi-Persona End-to-End Sequence Diagram](file:///c:/Users/avadu/26265/docs/DIAGRAMS.md#11-feature-10-complete-multi-persona-end-to-end-sequence-diagram)**:
    Chronological interaction flow among Institution, Regional Officer (Maker), Regional Officer (Checker), Bureau Approver, and Independent Auditor.
