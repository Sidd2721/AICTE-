# CHARTER — what makes the AICTE Deposit/FDR Portal RUNNABLE and WINNABLE

Read this together with docs/BRIEF.md. BRIEF says what to build and in which order. This file says
what the build must be like when a judge touches it. If they conflict, safety invariants in BRIEF
win; otherwise this file wins on priorities.

## 1. The win statement (north star)
A judge from AICTE, in six minutes and without our help, sees the full deposit lifecycle on
realistic data, trusts every number on screen, cannot make it fail, can verify every claim
themselves, and finds that the team can open and explain any part of the code.
Priority order when anything conflicts: RUNNABLE > CORRECT > CONVINCING > COMPLETE > POLISHED.
A smaller product that always works beats a bigger one that fails once on stage.

## 2. What we know about the competition (third-party reports; confirm officially)
- Smart India Hackathon 2026: launched 21 Aug 2026; idea-PPT screening Oct-Nov; 1-hour
  non-stop grand finale at nodal centres in December. Teams of 6 from one institute, at least
  one woman. Idea submission includes a PDF presentation.
- Judges are reported to be a panel from the problem-statement owner plus industry, with periodic
  mentor visits and a final demo and pitch. Reported criteria include innovation, technical
  feasibility (architecture, security, scalability, deployability), impact and presentation.
- AI tools are generally allowed, but the team must be able to explain and defend every part.
  Evaluators reportedly ask: who owns it, where the data lives, what it costs for a year,
  what breaks, how much AI wrote, how much is open source, and "open the code you just showed".
- NOT confirmed: whether software teams may bring pre-built code to the finale, how templates and
  open source must be disclosed, and the official rubric. Treat as an open risk (section 12).
- The problem owner is AICTE. The judges know the approval process and the handbook. Wrong
  rule numbers will be noticed; correct, clause-cited ones will be rewarded.

## 3. RUNNABLE standard (acceptance checks; each is a test or a scripted check)
R1 One command from a fresh clone to a running, seeded demo. Targets: under 10 minutes with
   downloads on an 8 GB laptop, under 2 minutes on a warm cache. Measure and record.
R2 A "doctor" command checks prerequisites (container runtime running, ports free, disk,
   versions) and prints plain-language fixes.
R3 Zero manual secrets in demo mode (safe generated or documented demo values). Production mode
   refuses defaults, placeholders, simulators and seeded users.
R4 Deterministic seed with named scenarios (section 6). Full reset to the same state in under
   60 seconds. Idempotent.
R5 Works offline after images are pulled: no CDN, web fonts or analytics. Measured: the built
   frontend has no external font or CDN references; remove template branding links (the template
   footer still links to its own social profiles).
R6 Resource budget (measured here): one backend worker uses about 127 MB, the template's default of
   four workers about 638 MB; database idle about 64 MB; built frontend about 876 KB; ready in
   1.4 to 7.4 seconds. Demo mode runs ONE worker (also makes in-memory limits and any in-process
   scheduler correct). Whole stack target under 1.5 GB; verify on the real compose stack.
R7 A visible system-status panel: database, scheduler last run, clock (and offset), simulators,
   version and mode.
R8 Works on Windows (container desktop with PowerShell or Git Bash), Linux and macOS. Handle line
   endings, paths and port conflicts. Provide the command for each shell.
R9 Reproducible: lockfiles, pinned base images and versions, tagged release, and an offline bundle
   (exported images plus docs) for a laptop with no internet.
R10 Linux CI runs the full gate AND a smoke test of the one-command path on every commit.
R11 Mode model: development, demo, production. Demo allows simulators, placeholders and seeded
   users but they are admin-only, bannered, and protected; production forbids all of it.
R12 Failure ladder with a pre-flight checklist: local run, deployed copy, recorded video,
   screenshots. Recovery from any failure in under 60 seconds.
R13 docs/RUN.md (one page), troubleshooting top ten, docs/LIMITS.md (what is simulated).
R14 Time machine presets: today, +15, +30, +45 days, overdue; reversible; shown on screen.

Deployed copy (demo only, synthetic data): free web tiers sleep after 15 minutes idle, wipe local
files on restart, expire free databases after 30 days, and may not offer free background workers.
So: one service built from the template's own image (it serves the frontend), documents stored
encrypted in the database, the daily job in-process under the lock or triggered by an authenticated
endpoint, a one-command reseed, a "demo, synthetic data" banner, and a keep-warm check before any
presentation. Real data requires government-approved hosting.

## 4. WINNABLE standard
W1 Domain-true. Every rule on screen shows its handbook clause and edition. Verified numbers only;
   anything unconfirmed says "awaiting AICTE confirmation" and is editable by an admin without
   redeploying. Show handbook statuses and terms AICTE uses (deposit requested/received,
   affidavits 3, 4, 6, 9, lien, release paths).
W2 Full statement coverage. A "Statement coverage" page maps all 10 capabilities and the 6 test
   scenarios (new FDR, validity tracking, approaching maturity, renewal, discrepancy, authorised
   release) to the screen that shows each and the test that proves it.
W3 One-sentence idea: "Every fact is claimed or independently confirmed, with method, date and
   expiry, and the system proves it." Everything else supports this.
W4 Measured improvement. Baseline (spreadsheet and email) versus portal for six tasks, timed by
   the team with a written protocol; plus alerts on time, confirmation turnaround (labelled
   simulated), backlog visibility. Show method, sample size and limits.
W5 Break-me challenge. Judges can try to cheat: upload a forged or altered bank letter, a letter
   signed by the right bank for a different FDR, a tampered amount, a replayed link. The system
   rejects each with a specific reason. This is the strongest live proof of trust.
W6 Security credibility without overclaiming: invariants page, audit-chain verify button,
   role-isolation demo (other region and other institution see nothing), scan and test reports,
   and the plain statement that an empanelled audit is required before real use.
W7 Honest limits. A page listing what is simulated, what AICTE and banks must provide, the
   integration path, and the open questions. Judges reward being told the truth.
W8 Simple UX. Four-step institution flow, two-click officer flow, plain-language statuses,
   English and Hindi, keyboard-only works, never colour alone, mobile friendly.
W9 Deployability story: hosting needs, running cost for a year (estimate with stated
   assumptions), who owns the data, backups, handover, maintenance and what breaks.
W10 Explainability: architecture decisions recorded, repo map, each team member can open and
   explain their modules; every claim in the deck points to a screen or a test.
W11 Demo craft: 60-second pitch, 2-minute and 6-minute demos, pre-staged scenarios, no dead air.
W12 Resilience: section R12 ladder rehearsed twice.
W13 Disclosure: open-source and licence inventory, AI-assistance statement, what was prepared
   before the event versus built during it, matching the official rules.
W14 Submission artifacts: idea PDF deck, video, repository, live link, README, one-page summary.
Avoid: claiming live bank or AICTE integration; AI in the trust path (AI may prefill, never
verify); cluttered dashboards; happy-path-only demos; features nobody can explain.

## 5. What judges will probe (build the answer into the product)
Domain: "Is the 2x for leased property right?" -> clause shown. "Who is the competent authority?"
-> open question listed, rule is data. Fraud: "How do you stop fake FDRs?" -> break-me challenge.
Process: "What if the bank has no API?" -> pluggable channel, signed-letter flow, simulator labelled.
Control: "Can one official release money?" -> maker-checker, blocked live. Time: "What if the
handbook changes?" -> edit rule data, what-if simulator. Trust: "Can records be altered?" ->
audit verify names the tampered entry. Ownership: "Who maintains it?" -> docs and handover plan.
Cost: "What does it cost a year?" -> estimate page. AI: "How much did AI write?" -> honest
answer, spec-driven, tests, every member can explain.

## 6. Demo design
Seed scenario set (synthetic; fictional institutions; real bank names and public IFSC prefixes only;
fake numbers): 3 regions; about 40 institutions; about 120 instruments across all lifecycle
states; named scenarios the demo can jump to: S-A new FDR submission; S-B bank-confirmed and one
mismatch; S-C approaching maturity; S-D overdue and escalated; S-E renewal with history; S-F planted
discrepancies (20 planted, 20 clean, legitimate duplicate); S-G release blocked then approved;
S-H bank down; S-I break-me forgeries.
Six-minute script: 1 pitch (30 s) 2 institution adds FDR in four steps 3 officer sees needs-action and
requests confirmation 4 bank (simulated) confirms; badge flips; mismatch flagged 5 time machine to
30 days: reminder, then overdue and escalation 6 renewal links history 7 release: blocked, checker
approves, receipt verifies offline 8 break-me and role isolation 9 metrics, limits, close.
Always end on the metrics page and the "what is simulated" page.

## 7. Evidence map (every claim -> where it can be checked)
Maintain docs/EVIDENCE.md: claim, screen or URL, test name, command to reproduce. Nothing appears in
the deck that is not in this map.

## 8. Scope control
Tier 1 (demo-critical, never cut): ledger, provenance, bank channel gate, role isolation, audit,
clock and alerts, release with maker-checker, dashboard, break-me, runnable path.
Tier 2: discrepancy engine and fraud lab metrics, renewal chain, reports, English and Hindi.
Tier 3 (cut first): passkeys, legacy import, what-if simulator, extra reports, optional
OCR prefill (if built: human-confirmed, measured accuracy on synthetic documents, never marks a
field confirmed).
Freeze rule: stop new features 24 hours before any judged moment; only fixes and rehearsal.

## 9. Work packages (run in this order; each is its own agent conversation)
W0 Runnable foundation (after BRIEF P0). Build R1, R2, R5, R6, R8, R9, R10: one-command bring-up, doctor
  command, single-worker demo profile, offline check, template-branding removal, lockfiles and
  pinned images, Linux CI with a smoke test. Tests: smoke test passes on a clean checkout; offline
  check finds zero external references; resource numbers recorded. Done when a new machine runs the
  demo from the README alone.
W1 Mode model (after BRIEF P2). R3, R11: development, demo, production behaviours; admin-only
  protected simulator and time-machine routes in demo; production startup refuses defaults,
  placeholders, simulators, seeded users, superuser database role. Tests: each mode's allowed and
  refused behaviours; an unauthenticated visitor cannot touch a simulator.
W2 Seed and scenarios (grow with every BRIEF slice). R4, section 6: deterministic seed for 2 regions
  plus a third, officer and checker per region, two institutions in one region, bureau, auditor,
  admin; passwords from environment or generated; reset under 60 seconds. Tests: seed is idempotent;
  every named scenario can be jumped to; isolation holds on seeded data.
W3 Judge experience (after BRIEF P13). Landing page with "Start here", role switcher with one-click
  demo sign-in (demo mode only), guided tour per role, system-status panel (R7), time-machine
  presets (R14), Statement coverage page (W2), Limits page (W7), SIMULATED banners. Tests: every
  tour step reaches a real screen; no demo sign-in exists in production mode.
W4 Break-me challenge (after BRIEF P8). A page where a judge uploads or picks a forged letter and sees the
  specific rejection reason; includes the nine forgery cases from the gate plus replayed and expired
  links. Tests: each case rejected for its intended reason; a genuine letter accepted.
W5 Evidence and metrics (after BRIEF P15). Baseline protocol and timing sheet for six tasks, metrics
  page, fraud lab TP, FP, FN, evidence pack export, published test and scan reports, EVIDENCE.md.
  Done when every number in the deck can be regenerated by one command.
W6 Presentation kit. Draft the idea deck (problem, why now, solution in one sentence, architecture,
  trust model, demo screenshots, measured results, feasibility and cost, roadmap, team and roles),
  the 3-minute video storyboard, the one-page summary, architecture and data-flow diagrams, and a
  README with a QR to the live copy. Every slide cites EVIDENCE.md.
W7 Q&A bank. 40 likely questions grouped by domain, security, process, ownership, cost, AI and
  open source, each with a 3-sentence answer and the screen or test that proves it. Include the
  honest answers for "how much did AI write" and "what is simulated".
W8 Resilience drills. Pre-flight checklist (machine, network, ports, seed, clock, accounts,
  browser, projector resolution, backups), the failure ladder, chaos drills (stop the database,
  kill the worker, change the clock, wrong browser zoom), a recovery card. Done when a stranger
  recovers from each drill in under 60 seconds using only the card.
W9 Disclosure and licences. Software bill of materials, licence inventory (including the design
  system's licence and emblem restriction), AI-assistance statement, prebuilt-versus-built
  timeline from git history, and a summary matching the official rules once confirmed.
W10 Deployed demo (after W0 to W4). Single-service deploy, reseed command, keep-warm check, banner,
  admin-only simulators, documented limits of the free tier. Done when the live link survives a
  restart and a reseed.
W11 Finale playbook (section 10) and role cards for the six members.
W12 Final audit. A fresh-context review against every R and W item, the BRIEF invariants, and
  a clean-machine run, twice. Report PASS or FAIL with evidence.

## 10. The 36-hour finale plan (adapt after the rules are confirmed)
If pre-built work is allowed: hours 0-2 verify environment and run the doctor and smoke test; 2-6
meet the mentor, absorb the problem owner's priorities, choose the delta; 6-24 build the delta
(requested scenarios, domain corrections, polish) in thin slices, each gated; 24 freeze; 24-30
evidence, deck, video, Q&A; 30-34 rehearse three times; 34-36 submission and buffer.
If everything must be built during the event: follow Tier 1 order from BRIEF (P0, P1, P2, P3, P6, P7,
P8, P10, P12, P13) with W0 and W2 in the first six hours, cut Tier 3, and use the agent on
one slice per conversation with the independent review after each.
Roles for six: product owner and presenter; backend lead (security, data); backend workflow
(scheduler, release); frontend and UX; QA, data and evidence; operations, docs and presentation.
At least one woman is required by the team rules. Every member owns and can explain a module.

## 11. Definition of ready to submit
All R and W items pass or are explicitly waived with a reason; gate green twice; clean-machine run
from the README succeeds; offline bundle works; live link alive; video watched end to end; deck
claims all map to EVIDENCE.md; disclosure and licence documents present; rehearsal done twice;
a backup of everything on a second device.

## 12. Open risks to resolve with people, not with code
Official rules on pre-built code, templates, open-source disclosure and AI use; the official rubric;
venue network and power; laptop spec; whether the problem owner provides rule clarifications or
sample data; the open handbook questions in docs/OPEN-QUESTIONS.md. Ask the SPOC and the nodal
centre in writing and file the answers in docs/RULES-CONFIRMED.md.
