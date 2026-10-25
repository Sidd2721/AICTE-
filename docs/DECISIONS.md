# DECISIONS.md — FDR Portal (AICTE PS 26265)

Architecture decisions and resolved questions. One entry per decision.
Format: `D-NNN | Slice | Date | Decision | Rationale | Status`

---

| ID   | Slice | Date       | Decision                                                                                           | Rationale                                                                                                  | Status    |
|------|-------|------------|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|-----------|
| D-01 | M0    | 2026-10-25 | **4 database roles**: `institution`, `regional`, `bureau`, `auditor`                              | BRIEF-PATCHES.md P-6: officer+checker both map to `regional` with a permission flag; admin = bureau + `is_superuser`. Simplifies policy count. | Decided   |
| D-02 | M0    | 2026-10-25 | **No FORCE ROW LEVEL SECURITY on audit tables**                                                   | Audit functions are SECURITY DEFINER and run as the owner. FORCE would require every call to set context first, breaking the append guarantee. FORCE is optional on tenant tables but untested — decide per table in M1. | Decided   |
| D-03 | M0    | 2026-10-25 | **Token lifetime: 60 minutes** (template default is 8 days)                                       | I11 and M0 requirements; template must be patched.                                                         | Decided   |
| D-04 | M0    | 2026-10-25 | **`.env` untracked from git** (`git rm --cached .env`)                                            | I9; `.env.example` is tracked instead.                                                                     | Decided   |
| D-05 | M0    | 2026-10-25 | **Python 3.14 required** (never lower)                                                             | Code uses `except A, B:` syntax; verified by starter tests.                                                | Decided   |
| D-06 | M0    | 2026-10-25 | **Unsigned uploads accepted but flagged** (not silently rejected)                                  | BRIEF-PATCHES.md P-7. Rejecting silently is worse than surfacing the gap for officer scrutiny.             | Decided   |
| D-07 | M0    | 2026-10-25 | **PostgreSQL version: PostgreSQL 16** (`postgres:16`)                                              | Pinned to postgres:16 so verified starter SQL in `starter/sql/` and `starter/py/rls_context.py` works out of the box. Compose path `/var/lib/postgresql/data`. | Decided   |
| D-08 | M4    | 2026-10-25 | **Manual-review path for bank replies** kept alongside I3 gate                                     | If bank re-saves PDF before signing, byte-prefix check fails on genuine reply. See OQ-016.                 | Decided   |
| D-09 | M2    | 2026-10-25 | **Starter rule files are DEMO** — app refuses to start outside development until CONFIRMED          | I7; BRIEF.md section 3. All amounts in starter/rules/*.json are placeholders.                              | Decided   |

---
_When a check fails twice, stop and write the cause here before continuing (BRIEF.md section 5, step 6)._
