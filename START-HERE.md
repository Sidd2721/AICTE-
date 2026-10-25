# fdr-agent-pack — what is in this folder

- BRIEF-PATCHES.md   Corrections and a scope trim for your BRIEF.md. Read first.
- AGENTS.md          Short rules file for the coding agent (copy to the repository root).
- .agents/AGENTS.md  One-line pointer, in case your agent reads rules from .agents/.
- starter/sql        Tested PostgreSQL: roles, schema (12 tables; one is a stub of the template user table), audit functions, RLS and grants.
- starter/py         Tested Python: trust badge, dated rules + startup guard, next_action(), RLS context helper,
                     strict bank-reply gate, CSV formula guard.
- starter/rules      Three DEMO rule files (all amounts are placeholders).
- starter/tests      26 database behaviour checks + 47 unit tests.
- scripts/check.sh   The gate for the template repository. scripts/verify-pack.sh re-runs everything in starter/.

Verified on: Python 3.14.9, PostgreSQL 16, fresh database, fresh virtual environment.
Not verified: PostgreSQL 18, Docker stack, Playwright, scanners, Antigravity itself.
