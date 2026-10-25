# PROMPTS.md — Slice Report Format (FDR Portal AICTE PS 26265)

Every slice report must use this format exactly. The agent cannot say "done" without all sections.

---

## Report Template

```
## Slice: [Slice ID and name]
**Date:** YYYY-MM-DD

### Files changed
- `path/to/file` — what changed and why

### Tests added
- `test_name` — what it proves
- ...

### Gate output (real tails — no truncation)
```
== backend tests
... (last 5 lines of pytest -q output)
== backend lint/types
... (last 5 lines of lint output)
ALL CHECKS PASSED
```

### "Done when" items
| Done-when criterion | Proving test | Result |
|---------------------|-------------|--------|
| ... | `test_name` | ✅ / ❌ |

### Open questions raised this slice
- [OQ-NNN] Question text (added to docs/OPEN-QUESTIONS.md)

### Risks
- Risk description and mitigation

### Notes
- Anything the next slice should know
```

---

## Example (filled in)

```
## Slice: M0 Harden the template
**Date:** 2026-10-26

### Files changed
- `backend/app/api/routes/users.py` — removed /signup route; returns 404
- `backend/app/core/config.py` — ACCESS_TOKEN_EXPIRE_MINUTES = 60
- `backend/.env.example` — added; `.env` removed from git tracking
- `compose.yml` — postgres image pinned to postgres:16 (D-07 resolved)

### Tests added
- `test_signup_returns_404` — proves /signup is gone
- `test_token_expires_in_60_minutes` — proves token lifetime
- `test_app_role_is_not_superuser` — proves rolsuper=false
- `test_env_is_not_tracked` — proves git ls-files fails on .env

### Gate output
```
== backend tests
....................................................                                         58 passed in 0.42s
== backend lint/types
Success: no issues found in 12 source files
ALL CHECKS PASSED
```

### "Done when" items
| Done-when criterion | Proving test | Result |
|---------------------|-------------|--------|
| signup returns 404/405 | `test_signup_returns_404` | ✅ |
| token life = 60 min | `test_token_expires_in_60_minutes` | ✅ |
| runtime role not superuser | `test_app_role_is_not_superuser` | ✅ |
| .env untracked | `test_env_is_not_tracked` | ✅ |
| baseline suite passes | (all 58 pass) | ✅ |
```
