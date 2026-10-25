# BRIEF — AICTE Security Deposit / FDR Portal (PS 26265) — MVP

Read this whole file at the start of every slice. It is the single source of truth for the MVP. If another file
disagrees, this file wins. The original long brief is kept as docs/BRIEF-FULL.md for STRETCH ideas only; do not
build from it. Context: prototype for a government regulator; synthetic data only; there is NO real bank or AICTE
integration; every such adapter is a labelled simulator.

## 1. Mission, MVP definition, non-goals

Mission: every security deposit or FDR held by AICTE has one record, an owner, a next action and a deadline, and
every fact is marked CLAIMED or BANK-CONFIRMED with method and date.

The MVP is done when ALL of these are true:
1. The ten statement capabilities work end to end on synthetic data (table in section 6.2).
2. Each of the six statement scenarios is an automated end-to-end test: new FDR submission; validity tracking;
   approaching maturity; renewal; discrepancy identification; authorised release.
3. Measured, labelled-synthetic results exist: discrepancies caught out of 20 planted, false positives on clean
   records, alerts fired on time, time to confirmation (simulated), and a six-task baseline-versus-portal timing sheet.
4. It builds from a clean setup, passes the gate (`bash scripts/check.sh`), and the seven-step demo runs twice from
   the documents alone.
Non-goals: real bank or AICTE live integration, native app, ML fraud scoring, payment movement, SMS, Hindi, UX4G,
admin console, legacy import (all STRETCH, section 8).

## 2. Roles (decided; see docs/DECISIONS.md D5)

Four database roles, stored in `user.role`: `institution`, `regional`, `bureau`, `auditor`.
- institution: reads and writes only its own institution's records.
- regional: the regional officer. Reads and writes its own region. Verifies release requests (maker side).
- bureau: all regions. Approves release requests (checker side). Admin = a bureau user with the template's
  `is_superuser` flag (creates users). No separate admin or checker role.
- auditor: reads everything, writes nothing.
- The bank officer has no account: a one-time link only.
Release chain: institution requests, regional officer verifies, bureau approves. verified_by is never approved_by
(database CHECK). The database does NOT decide which role may approve; the service layer must, and tests prove it.
Users are created by an admin; there is no public sign-up. Access tokens last 60 minutes.
Database rule set (tested in starter/tests/sql_behaviour_check.py, 26 checks): institution sees only its own
institution; regional only its region; bureau and auditor everything; auditor writes are refused; nobody deletes;
no or unknown context sees nothing; audit rows are readable only by bureau and auditor and written only through
`audit_append()`. An auditor UPDATE that is blocked by policy raises or changes zero rows: assert row counts.

## 3. Rulebook (rule data only, never code constants; money in paise)

Source: AICTE Approval Process Handbook 2024-25 to 2026-27. Tags: [VERIFIED] two sources or the official PDF;
[COPY] third-party copy only; [OPEN] not confirmed.
- Deposit by programme level, in lakh (paise = lakh x 10,000,000) [VERIFIED]: Engineering and Technology: Diploma 15,
  UG 35, PG 15. Planning, Applied Arts and Crafts, Design, Hotel Management and Catering Technology: 15, 15, 15.
  Computer Applications: UG 5, PG 15. Management: UG 5, PG 15. No diploma for Computer Applications or Management.
- Double for private leased building or land; sum of each programme and level applied for; 10-year term;
  withdrawable after 10 years or on closure [COPY]. Exempt: regulatory bodies, government institutions; no deposit
  where an NOC for release of an earlier FDR was already issued [COPY: 2020-21 deck]. Re-check in the official PDF.
- Proof of payment plus Affidavit 3 within 15 days of intimation [VERIFIED]. Late penalty: 10% and then 20% or 50% by
  30 May and 31 July, then approval withdrawn [OPEN: copies disagree]. Treat as placeholder.
- Release (online): request letter, Affidavit 6, copy of the instrument or payment proof [COPY]. Change of bank
  details: Affidavit 9 [COPY]. Affidavit 4 = closure [OPEN]. University conversion requires no pending complaints or
  disciplinary proceedings [COPY]. Progressive closure requires a certificate from the affiliating university or board
  that no students remain, not needed if the deposit already matured [COPY]. Merger: same certificate for the child
  institution [COPY]. Regional officer NOC [OPEN].
- Uploaded documents are expected to carry a Digital Signature Certificate. Decision: unsigned uploads are accepted,
  shown as "unsigned" and flagged for scrutiny, never silently rejected. A DSC proves who signed; it is NOT bank
  confirmation.
- A 2026-27 addendum exists. Key rule versions by handbook edition AND addendum.
Starter rule files (starter/rules/*.json) hold DEMO values and status "DEMO". The app refuses to start outside
development while any rule file is not "CONFIRMED". List every unconfirmed item in docs/OPEN-QUESTIONS.md.

## 4. Invariants (never violate)

I1  A field is "confirmed" only through a confirmation row. The badge is computed, never stored:
    claimed | confirmed | stale | changed (edited after confirmation). Code: starter/py/trust.py.
I2  Bank source down gives status "unavailable", shown as "source unavailable", never "mismatch".
I3  A bank reply is accepted only through the full gate in starter/py/bank_gate.py: it begins with the exact bytes of
    the letter we issued; exactly one signature; intact AND valid AND trusted; the signature covers the whole file;
    the signer is the certificate pinned for that bank; the certificate has non-repudiation key usage.
I4  Runtime connects as NOSUPERUSER, NOBYPASSRLS. Call `set_rls_context()` right after authentication (it applies the
    context to the already-open transaction AND records it for later ones). No context means no rows. No RLS on the
    user table. Code: starter/py/rls_context.py.
I5  Audit is written only through `audit_append()` (SECURITY DEFINER, advisory lock, hash chain). Update, delete and
    truncate are blocked by triggers. The application refuses floats, NaN and non-string keys in payloads before
    calling it. `audit_verify()` must return NULL in CI. SQL: starter/sql/audit.sql.
I6  Money is integer paise. Store UTC, display IST.
I7  Rules are dated JSON. DEMO or placeholder values block startup outside development.
I8  Maker is never checker (database CHECK plus service check). The system recommends and records; it never moves
    money or instructs a payment.
I9  No secrets, tokens, FDR numbers or real personal data in code, logs, tests, prompts or git. `.env` is not tracked.
I10 Every endpoint: authentication dependency, RLS test, audit event for every state change, test. Cross-scope writes
    return 403 with a clear message, never 500.
I11 Invite-only users; no public sign-up; 60-minute tokens; login is rate limited.
I12 Handbook numbers come only from section 3 as rule data. Unconfirmed means placeholder plus an open question.
I13 A DSC proves who signed a document; it is not bank confirmation.
I14 Primary buttons come from `next_action()` (starter/py/next_action.py). No action logic in the UI.
I15 Simulators exist only under /sim or the adapter registry, only when FASTAPI_ENV == "development", always with a
    visible "SIMULATED" label, and a test proves they are absent otherwise.

## 5. Working method and commands

Per slice: 1 read this file and the slice; 2 write the tests for every "Done when" item and show them failing;
3 implement in thin steps, one commit per slice; 4 run the gate and the slice tests, rebuild a database from nothing
(roles script, migrations, `uv run alembic check`) and run them again; 5 report in the format of docs/PROMPTS.md;
6 stop if any check fails twice and write the cause in docs/DECISIONS.md. Never disable, skip or loosen a check;
never edit a test to pass unless this file says the behaviour changed (say so). Ask the human before: a new
dependency, a destructive migration, an authentication change, anything touching .env, compose or deployment files
(M0 is pre-approved to edit compose.yml and .env.example).
Commands (all verified on the template):
- Backend tests `cd backend && uv run bash scripts/test.sh` (template baseline: 58 pass)
- Backend lint/types `cd backend && uv run bash scripts/lint.sh`
- Frontend read-only check `cd frontend && bunx biome check --no-errors-on-unmatched --files-ignore-unknown=true ./`
- Frontend build `cd frontend && bun run build` (output goes to backend/app/frontend, git-ignored)
- Whole gate `bash scripts/check.sh`; starter code `PGPASSWORD=<pw> PY=<python3.14> bash scripts/verify-pack.sh`
- Migrations `cd backend && uv run alembic revision --autogenerate -m "<msg>"`, read it, `uv run alembic upgrade head`,
  then `uv run alembic check`
- After any API change `bash scripts/generate-client.sh`; it ends with `bun run lint`, which REWRITES files: read the diff.
Python 3.14 is required; never lower it. DATABASE_URL = runtime role; MIGRATION_DATABASE_URL = owner role.
Where starter code goes: backend/app/domain/{trust,rules,next_action,bank_gate,csv_safe}.py, backend/app/core/rls_context.py,
backend/app/rules/*.json, tests under backend/tests/. After copying, change the imports (`from trust import` becomes
`from app.domain.trust import`). SQL is the specification: put its text into Alembic migrations.

## 6. Slices (strictly in order; every slice includes its screens, tests and audit events)

### 6.1 Slice list

M0 Harden the template. Needs: none.
 Build: remove the sample Items feature everywhere (backend, frontend routes, generated client, e2e tests such as
 frontend/tests/items.spec.ts); remove the /signup route and page; tokens 60 minutes; SECRET_KEY must be 32+ bytes
 outside development; `git rm --cached .env` and add .env.example; create roles `migrator` and `app` (adapt
 starter/sql/roles.sql, database name `app`); DATABASE_URL for app, MIGRATION_DATABASE_URL for Alembic (edit
 alembic env.py); decide the PostgreSQL major version (docs/DECISIONS.md D7) and match the compose data path; replace
 sign-up based e2e helpers with an admin-API user-creation helper; keep a minimal "Deposits" page so navigation compiles.
 Tests first: signup returns 404 or 405; token life is 60 minutes; app role has rolsuper false and rolbypassrls false;
 `.env` untracked; baseline suite passes (list which template tests you removed).
 Done when: backend gate and tests pass, frontend check and build pass, client regenerated, a fresh database builds
 from migrations alone and `alembic check` is clean.
 Evidence: gate output tails; test counts before and after; list of removed files.

M1 Schema, access, audit. Needs: M0.
 Build: SQLModel models and Alembic migrations that match starter/sql/schema.sql (12 tables; extend the template
 user table with role, region, institution_id); hardening.sql (grants, RLS) and audit.sql (functions, triggers) as
 migrations; every new required column has a server default; `set_rls_context()` called in the authentication
 dependency right after the user is loaded, with role, region and institution; 403 for cross-scope writes; an
 `audit()` helper that validates payloads and calls `audit_append()`; /audit/verify (bureau, auditor); a signed daily
 checkpoint function (job wiring comes in M5); login rate limit (ask the human which library, the template has none).
 Tests first: port ALL 26 checks of starter/tests/sql_behaviour_check.py into backend/tests by name; API-level
 isolation per role; context survives a mid-request commit; auditor writes refused; nobody deletes; no context sees
 nothing; app role flags; RLS coverage guard (every table with instrument_id or institution_id has RLS).
 Mutation proof: weaken the policies (institutions see their region; auditors may update; allow delete), show the
 tests fail, then restore.
 Done when: removing every application-level region filter leaks nothing; audit_verify() is NULL; tampering is
 detected and names the row; starter/tests/test_rls_late_context.py logic is covered by a backend test.

M2 Rules, clock, "what do I owe". Needs: M1.
 Build: copy the rule files and starter/py/rules.py; startup guard wired into app startup; clock service (offset
 stored in the database, honoured only in development; /sim/clock endpoints); institution registry (programmes as
 JSON, leased_private, is_government); deposit engine: sum across programmes, double for private leased property,
 exemption with reason, result shows rule version, status DEMO or CONFIRMED, and the consequence of missing the
 deadline; institution screen "My deposits" with what is owed and the next deadline.
 Tests first: copy starter/tests/test_rules_files.py and test_trust_rules.py (rules part); owned versus leased;
 several programmes; government institution owes nothing and shows why; changing a rule file changes the result with
 no code change; startup refuses DEMO rules when FASTAPI_ENV is not development.
 Done when: every number on screen traces to a rule file and shows a DEMO label until confirmed.

M3 Submission and vault. Needs: M2.
 Build: instrument create for kinds FDR and RTGS; draft autosave; the four-step institution flow (sign in, upload or
 photograph, check the pre-filled fields, submit); upload endpoint with content-based type check (PDF, JPEG, PNG by
 magic bytes), size cap, SHA-256, never-overwrite versions, duplicate detection by hash, encryption at rest with
 AES-GCM and the record id as associated data, key outside the database (ask before adding a dependency if
 `cryptography` is not already installed); signature display: "signed by X, valid or invalid" or "unsigned"
 (pyHanko, ask first); screens: Add deposit, Deposit detail with documents.
 Tests first: disguised executable rejected; same file twice detected; changed file becomes version 2; a document
 cannot be decrypted under another record; nothing is "confirmed" after submission (badge claimed); unsigned shown.
 Done when: an institution submits an FDR and a payment proof end to end (Playwright).

M4 Bank channel, provenance, discrepancy checks. Needs: M3.
 Build: adapter interface with the bank simulator and an email gateway only (labelled SIMULATED); bank registry
 (bank_code, contact email, pinned certificate sha256); confirmation request: issued letter PDF with reference, QR
 optional, bytes and hash stored encrypted (ask before adding a PDF library), one-time token from
 `secrets.token_urlsafe(32)` stored only as a hash, 14-day expiry from a rule, marked used in the same transaction as
 acceptance; public bank-reply endpoint (PDF only, small size cap, throttled) using the I3 gate; on success write a
 confirmation row with a field snapshot and expiry from a rule; on gate failure status rejected with the reason code;
 simulator down gives unavailable; badge via starter/py/trust.py. Discrepancy checks as pure functions with stable
 codes and severity: D1 duplicate_reference (block): same bank_code and ref_no on another institution, or at the same
 institution unless the instrument is marked is_duplicate_receipt AND has an indemnity document; D2 total_below_required
 (warn): sum of non-released instruments below the required deposit; D3 maturity_not_after_issue (block); D4
 future_dated_issue (warn, by the clock); D5 bank_ifsc_mismatch (block): IFSC first four characters differ from
 bank_code, bank_code not in the bank list, or IFSC fails ^[A-Z]{4}0[A-Z0-9]{6}$; D6 missing_documents (block) from the
 timelines rule. Flag waiver needs a reason of at least 10 characters. Case notes. Officer screens: "Needs action" and
 "Case" with the single primary button from next_action(). Accepting a record moves pending to active and needs docs
 complete and no unwaived block flag.
 Tests first: copy starter/tests/test_bank_gate.py (9 cases); expired and reused tokens rejected; bank down gives
 unavailable; badge goes claimed, confirmed, changed, stale; each discrepancy has a positive and a negative test
 including a legitimate duplicate that is NOT accused; waiver rules; every state change emits an audit event.
 Done when: an officer takes a case from submitted to active using only the Case page.

M5 Obligations, worker, alerts, renewal. Needs: M4.
 Build: obligations from instruments and rules (confirmation_due, maturity, renewal_due, payment_proof with a
 placeholder deadline); a separate daily worker (own compose service, `python -m app.jobs.daily`) with an advisory
 lock, idempotent through UNIQUE(obligation_id, step) and `ON CONFLICT DO NOTHING`; reminders at the rule offsets;
 overdue escalation along the rule ladder; email through Mailpit; in-app notifications and acknowledgement; lifecycle
 active becomes matured when the clock passes maturity; signed daily audit checkpoint scheduled here; renewal:
 replacement instrument linked through replaces_id, a coverage-gap flag D7 when the new issue date is after the old
 maturity, full history timeline, old instrument becomes renewed when the replacement is accepted; lost-FDR duplicate
 path (is_duplicate_receipt plus indemnity checklist).
 Tests first: clock +30 days gives exactly one reminder; running twice adds none; two concurrent runs stay idempotent;
 an unacknowledged alert escalates one step per interval; a delivery failure retries then escalates to a person; a gap
 raises D7; the chain keeps history.
 Done when: the clock demo shows reminder, overdue and escalation in order and the email appears in Mailpit.

M6 Release. Needs: M5.
 Build: release request for the four paths (term_completion, closure, merger, conversion) with the checklist from
 starter/rules/release_paths JSON; institution requests and uploads each item; regional officer verifies; bureau
 approves; reject path; blocks for open block flags, stale or changed confirmation, missing documents; closure item
 waived when the deposit already matured; conversion requires the officer's manual attestation "no pending complaints";
 penalty display from rules (placeholder); signed receipt with PyJWT, algorithm pinned, payload holds a random receipt
 id, issue time and a short instrument hash, no amounts and no personal data; public verify page plus a script that
 verifies offline with only the public key; lifecycle becomes released. The system never instructs a payment.
 Tests first: verifier is never approver (database CHECK and service); institution, regional and auditor cannot approve;
 any open block flag blocks; each path shows exactly its own checklist; the matured-closure waiver; receipt tamper,
 wrong key and "alg none" attacks fail.
 Done when: the demo release runs from request to receipt and verifies on a second machine with the public key only.

M7 Dashboard, search, reports. Needs: M6.
 Build: six counters via `dashboard_bucket()` (active, expiring, matured, renewed, released, pending), "Needs action
 today" ordered by urgency with one primary action per row, search (reference, institution; filters region,
 lifecycle, badge), a permitted-field update matrix with audit events, four CSV reports (pending verifications, upcoming
 maturities, missing documents, cases needing intervention) through `csv_safe`; the bureau dashboard screen.
 Tests first: counters change after each lifecycle step; region scoping; CSV formulas neutralised; report rows equal the
 database; next_action matches the truth table in starter/tests/test_next_action.py.
 Done when: an officer works a typical day from the needs-action list in two clicks per item (Playwright).

M8 Polish, accessibility, fraud lab, metrics. Needs: M7.
 Build: finish the six screens (My deposits, Add deposit, Deposit detail; Needs action, Case; Dashboard); plain-language
 statuses ("Waiting for bank confirmation", "Bank-confirmed on <date>", "Matures in <n> days", "Overdue by <n> days");
 never colour alone; empty and error states that say what happened and what to do; the SIMULATED banner; keyboard-only
 pass; screen-reader pass; fraud lab: synthetic data with 20 planted discrepancies, 20 clean records and legitimate
 duplicates, reporting true positives, false positives and false negatives; metrics page; docs/TIMING.md for the
 six-task baseline-versus-portal sheet; the six statement scenarios as end-to-end tests.
 Done when: the six scenario tests pass, the fraud lab numbers print in a test and on the metrics page labelled
 synthetic, and an accessibility findings list exists with all blocking items fixed.

M9 Hardening, deployment, documents, demo. Needs: M8.
 Build: security headers and a strict content-security policy (the frontend keeps its token in browser storage, so no
 third-party scripts); rate limits on login and the bank-reply page; structured logs without sensitive values; health
 checks; alerts on job failure and "no scheduler run in 24 hours"; saved reports from secret scan, dependency scan, SBOM
 and a baseline web scan in docs/reports/; production compose with a separate worker, non-superuser role and simulators
 off; production refuses to start with default secrets or DEMO rules; nightly backup and one rehearsed restore; guides
 for administrator, officer, institution and bank officer; architecture and data-flow note; a security and privacy
 summary stating what is and is not certified; docs/OPEN-QUESTIONS.md current; the seven-step demo: submit an FDR in four
 steps; bank confirms and one mismatch is flagged; clock to 30 days shows reminder, overdue and escalation; renewal links
 history; fraud lab results; release blocked then approved and the receipt verified offline; bank down shows "source
 unavailable".
 Done when: the startup refusal is tested, scan reports and the restore drill are saved, and a person who has never seen
 the system runs the demo from the documents alone, twice from a clean setup.

### 6.2 Coverage of the statement
Capability 1 repository: M1, M3. 2 documents: M3. 3 verification and discrepancies: M4. 4 validity tracking: M5.
5 renewal: M5. 6 release and refund: M6. 7 alerts and escalation: M5. 8 dashboard and reports: M7. 9 audit and access
control: M1. 10 integration and security: M4 (adapters), M9 (hardening).
Scenarios: new FDR submission M3, validity tracking M5, approaching maturity M5, renewal M5, discrepancy identification
M4, authorised release M6; all six as end-to-end tests in M8.

## 7. Cross-cutting requirements
Security: least privilege; field-level protection for sensitive values; no secrets in code or logs; dependency and
secret scanning; a CERT-In or STQC-empanelled audit and a legal review are required before any real data.
Privacy: design for India's data-protection law (core duties from 13 May 2027, confirm in the Gazette): notice,
purpose limitation, retention rules, access requests, breach notification. Whether a government statutory body is
exempt is a legal question. Reliability: backups, restore drill, health checks. Accessibility: aim for WCAG 2.1 AA;
the screens use plain language and never rely on colour alone. Honesty: label every simulator, never claim
certification or live integration, report what you could not verify.

## 8. STRETCH (only after the full MVP demo runs twice)
Legacy import and interest-refund tracker; Hindi and English templates; UX4G tokens after a coexistence spike;
installable app; what-if simulator; admin console and maker-checker on rule changes; digests and delivery tracking;
passkeys; PDF reports; RTGS reconciliation queue; SMS; extension, forfeiture and bank-detail-change decisions;
holiday calendar; saved filters; session list and forced logout; evidence-pack export; deficiency-request cycles.
Mapping to the long brief: M0 = P0; M1 = P1+P2+P3; M2 = P4+P5; M3 = P7; M4 = P6+P8+P9; M5 = P10 (+ renewal part of P11);
M6 = P12; M7 = P13; M8 = P14+P15; M9 = P16+P17.

## 9. REVIEW prompt (fresh, read-only conversation, after M1, M4, M6 and M9)
Review the last slice as a hostile security and product reviewer. Try to break every invariant (I1 to I15) and every
"Done when" item of the slice. Report findings by severity with file and line, and list anything you could not verify.
Do not edit anything.
