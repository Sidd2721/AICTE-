# BRIEF-PATCHES.md — corrections and trims to BRIEF.md

Apply these to BRIEF.md before the agent starts. Where a patch contradicts BRIEF.md, the patch wins.
Tags: [RAN] I executed it. [READ] I read the file or page. [2 SOURCES] two independent documents agree.
[SINGLE] one source only. [OPEN] unverified, ask a human.

## A. Facts in BRIEF.md that I checked and found correct (keep)

1. Deposit table (lakh): Engineering and Technology 15 / 35 / 15 (Diploma / UG / PG); Planning, Applied Arts and
   Crafts, Design, Hotel Management and Catering Technology 15 / 15 / 15; Computer Applications and Management:
   UG 5, PG 15, no diploma. [2 SOURCES] draft handbook copy and an official-site handbook PDF snippet ("Table 1.4").
2. Multiple programmes or levels pay the sum; 10-year term; withdrawal after 10 years or on closure. [READ] handbook-based guidelines text.
3. Penalty percentages conflict between copies (10% and 20% in one, 10% and 50% in another, with 30 May / 31 July
   cut-offs). Keep them as placeholders. [READ] confirmed the conflict exists.
4. "No deposit where an NOC was already issued for release of the earlier FDR" and "regulatory bodies are exempt".
   [READ] AICTE's 2020-21 handbook-changes deck. Re-confirm in the 2024-27 official PDF.
5. Affidavit 3 = submitting the deposit [READ] official handbook copy. Affidavits 6 (release) and 9 (change in bank
   details) [READ] AICTE attachments page seen earlier. Affidavit 4 = closure is [OPEN]: not confirmed.
6. DPDP: core duties start 13 May 2027, consent-manager rules 13 Nov 2026. [2 SOURCES+] several law-firm notes.
   One firm says the Gazette publication date was 14 Nov 2025; confirm in the Gazette. My earlier "14 May 2027" is withdrawn.
7. Template facts: token default is 8 days (so 60 minutes needs a change); open /signup route exists; the access
   token is kept in browser localStorage; `.env` is tracked by git; Python 3.14 is required; the database image is
   postgres:18 with its data volume at /var/lib/postgresql. [RAN]
8. I4 is right: the user lookup opens the transaction before the role is known, so a listener alone leaves that
   first transaction with an empty context. Apply the context at once AND re-apply on later transactions.
   [RAN] listener-only returned 0 rows in the already-open transaction; the helper in starter/py/rls_context.py fixes it.
9. I3 is right and stricter than what I gave you earlier. "intact AND valid AND trusted" alone accepts a different
   document signed with a real bank key. [RAN] nine attack cases in starter/tests/test_bank_gate.py.

## B. Patches (changes to make)

P-1 Commands. Backend commands must run through uv. Use `cd backend && uv run bash scripts/test.sh` and
`uv run bash scripts/lint.sh` (plain `bash scripts/lint.sh` fails: mypy is not on PATH). [RAN]
Read-only frontend check: `cd frontend && bunx biome check --no-errors-on-unmatched --files-ignore-unknown=true ./`.
Frontend build: `cd frontend && bun run build` (output goes to backend/app/frontend, which is git-ignored). [RAN]
`scripts/generate-client.sh` ends with `bun run lint`, which rewrites files: review the diff. [READ]
The template's frontend e2e tests reference the Items feature (frontend/tests/items.spec.ts): remove or rewrite them in P0.

P-2 Database image (P0). BRIEF.md says pin to 16. The template ships 18. Pick one on purpose. All SQL in starter/ was
tested on PostgreSQL 16 only; if you keep 18, run `scripts/verify-pack.sh` against 18 first. [OPEN]

P-3 Forced RLS (I4). BRIEF.md says the owner is also bound by forced RLS. The tested design does NOT use FORCE: the
runtime role is not the owner, so RLS binds it anyway, and the audit functions run as the owner (SECURITY DEFINER)
and rely on that. If you add FORCE to tenant tables, the audit functions and every seed or backfill must set a context
first. FORCE on tenant tables is untested here. [OPEN] Recommended: no FORCE on audit tables; FORCE optional elsewhere.

P-4 Audit (I5). Implement as the SQL in starter/sql/audit.sql: `audit_append()` and `audit_verify()` are SECURITY
DEFINER, serialised by an advisory lock; update, delete and truncate are blocked by triggers; the runtime role cannot
insert into the table directly and can read it only as bureau or auditor. [RAN] 8 threads x 15 appends gave one linear
chain of 121 rows; a superuser edit was caught by id. The "no floats" rule cannot be enforced in SQL: enforce it in the
application before calling `audit_append`. The hash input uses jsonb text rendering; do not move the database between
major versions without re-running `audit_verify()`.

P-5 Who may approve (I8). The database enforces maker is not checker and region scope. It does NOT enforce which role
may approve a release. Enforce role-to-action in the service layer and test it. [RAN] only the CHECK and scope.

P-6 Roles. BRIEF.md has officer, checker, bureau, auditor, institution, admin. The starter SQL has four database roles
(institution, regional, bureau, auditor). Map officer and checker onto `regional` with a permission flag, and admin
onto `bureau` plus an app-level flag, or extend the policies. Decide once, write it in BRIEF.md section 2.

P-7 DSC on uploads (P7). BRIEF.md says unsigned documents are not valid yet the institution flow allows a photograph.
Resolve it as: unsigned uploads are accepted but shown "unsigned" and flagged for scrutiny, never rejected silently.
Whether AICTE accepts unsigned uploads is [OPEN] (add to docs/OPEN-QUESTIONS.md).

P-8 Bank replies (I3). The gate requires the reply to begin with the exact bytes of the letter we issued, which works
only if the bank signs by incremental update (the normal behaviour of PDF signing tools). If a bank re-saves the PDF,
the gate rejects a genuine reply. Keep a manual-review path (method "manual", lowest tier) and add the question to
docs/OPEN-QUESTIONS.md. [OPEN]

P-9 Handbook scope. A 2026-27 addendum exists (a news report says it changes supernumerary seats and takes some
management and computer-application programmes of non-technical institutions out of AICTE's purview). [SINGLE]
Key rule versions by edition AND addendum, and check whether the deposit table or its scope changed.

P-10 Shrink the scope (the most important patch). BRIEF.md has 18 slices; that is too much to finish and demo well.
Build CORE first, in order. Each CORE slice is trimmed as shown. Everything else is STRETCH: build only after the
whole CORE demo runs twice from a clean setup.

CORE (12 slices, trimmed):
- P0 Harden the template (as written, plus P-1, P-2).
- P1 Schema (use starter/sql/schema.sql as the reference; drop programme/property sub-tables if programmes stay JSON).
- P2 Identity, access, isolation (as written, plus the mutation proof). Skip session list and forced logout.
- P3 Audit trail (starter/sql/audit.sql). Skip the evidence-pack export; keep verify and the signed daily checkpoint.
- P4 Rules and clock only: dated rule files, startup guard, clock offset in development. Skip the admin console,
  maker-checker on rule changes, what-if simulator, template UI and holiday UI.
- P5 "What do I owe" calculator (as written).
- P6 Adapter framework: interface plus the bank simulator and the email gateway only. Skip SMS, statement import,
  AICTE records and the complaints feed (keep a manual attestation field for "no pending complaints").
- P7 Submission and vault (as written).
- P8 Provenance and bank channel with the full I3 gate. Skip RTGS reconciliation queue (list RTGS as manual).
- P9 Completeness and discrepancy checks, notes, flag waiver. Skip deficiency-request cycles.
- P10 Obligations, daily worker, reminders, escalation, acknowledgement. Skip digest and Hindi templates.
- P12 Release for the four paths, maker-checker, flag blocks, signed receipt. Skip extension/forfeiture decisions
  and bank-detail change approval.
- P13 Dashboard, needs-action list, search, four CSV reports. Skip PDF export and saved filters.
- P14 Screens: the six screens only, plain-language statuses, never colour alone, keyboard pass. Skip UX4G and Hindi.
- P15 Fraud lab and the six-task timing sheet.
- P16 Hardening: headers and content-security policy, login and bank-reply rate limits, secret and dependency scans,
  backup and one restore drill, production refuses defaults and placeholders.
- P17 Docs: demo script, administrator and officer guides, security summary, open questions.

STRETCH (in this order): P11 renewal and legacy import beyond the replacement link, Hindi, UX4G spike, installable
app, digests, what-if simulator, admin console, passkeys, PDF reports, RTGS reconciliation.
Keep from P11 in CORE only the replacement link, the coverage-gap check and the lost-FDR duplicate path, because the
statement's "renewal" scenario needs them (put them inside P9/P10 acceptance tests).

P-11 Gate. Replace the gate list in BRIEF.md section 5 with `bash scripts/check.sh` plus the slice's own tests.
Add `bash scripts/verify-pack.sh` after any change to SQL or the starter modules.

P-12 Statement alignment. The six statement test scenarios must each be an automated end-to-end test by P15:
new FDR submission, validity tracking, approaching maturity, renewal, discrepancy identification, authorised release.

## C. What I could not verify

- Official-PDF wording of the release clauses, the competent authority per path, and the "balance amount" rule.
- The 2026-27 addendum's effect on deposits.
- FORCE ROW LEVEL SECURITY with the audit functions; PostgreSQL 18 behaviour; Docker stack and Playwright runs.
- Rate-limit library choice (the template has none); content-security policy; UX4G licence and coexistence.
- Antigravity's rules-file location (root AGENTS.md versus .agents/AGENTS.md).
