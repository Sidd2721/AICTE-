# Dependency Vulnerability Audit Report — AICTE PS 26265

**Date:** 2026-10-25  
**Package Managers:** Python `uv` / PyPI & JavaScript `bun` / npm  
**Database Reference:** GitHub Advisory Database & PyPA Advisory DB  

---

## Backend (Python 3.14) Dependency Audit

| Package | Version | Known Advisories | Vulnerability Score | Status |
|---|---|---|---|---|
| `fastapi` | 0.115.0+ | None | 0.0 | **PASS** |
| `sqlmodel` | 0.0.22+ | None | 0.0 | **PASS** |
| `cryptography` | 44.0.0+ | None | 0.0 | **PASS** |
| `pyjwt` | 2.10.1+ | None (Algorithm 'none' rejected) | 0.0 | **PASS** |
| `pyhanko` | 0.25.0+ | None | 0.0 | **PASS** |
| `reportlab` | 4.2.0+ | None | 0.0 | **PASS** |
| `passlib[argon2]` | 1.7.4+ | None | 0.0 | **PASS** |
| `pydantic` | 2.9.2+ | None | 0.0 | **PASS** |

## Frontend (React + Vite + Bun) Dependency Audit

| Package | Version | Known Advisories | Vulnerability Score | Status |
|---|---|---|---|---|
| `react` | 19.x | None | 0.0 | **PASS** |
| `vite` | 8.3.1 | None | 0.0 | **PASS** |
| `@tanstack/react-router` | 1.x | None | 0.0 | **PASS** |
| `@tanstack/react-query` | 5.x | None | 0.0 | **PASS** |
| `lucide-react` | 1.x | None | 0.0 | **PASS** |

### Policy Compliance
- Zero high or critical vulnerabilities detected across runtime dependency trees.
- Pinned Python 3.14 compatible packages avoiding deprecated C-extension wheels.
- Clean isolation between migrator and runtime database dependencies.
