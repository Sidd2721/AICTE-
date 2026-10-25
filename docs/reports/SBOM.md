# Software Bill of Materials (SBOM) — AICTE PS 26265

Format: CycloneDX 1.5 Compliant Summary  
Target: AICTE Security Deposit / FDR Portal Prototype  

---

## 1. Primary Components

### Backend Runtime (Python 3.14)
- **Runtime Environment:** CPython 3.14 on Linux/Windows container base
- **Web Framework:** FastAPI (ASGI via Uvicorn)
- **Object Relational Mapper:** SQLModel 0.0.22 (SQLAlchemy 2.0 Core)
- **Database Engine:** PostgreSQL 16
- **Cryptography Engine:** `cryptography` (OpenSSL 3.x bindings)
- **Token Handling:** PyJWT (strictly RS256 / HS256, no alg=none)
- **PDF & Digital Signature:** PyHanko & ReportLab

### Frontend Runtime (SPA)
- **UI Engine:** React 19
- **Bundler:** Vite 8.3.1
- **Package Manager:** Bun 1.x
- **Routing:** TanStack Router
- **Data Synchronization:** TanStack Query

---

## 2. Cryptographic Algorithm Manifest

| Function | Algorithm / Primitive | Library | Key Size / Strength |
|---|---|---|---|
| Document Vault Encryption | AES-256-GCM with AAD | `cryptography.hazmat.primitives.ciphers.aead.AESGCM` | 256 bits |
| Audit Ledger Chain | SHA-256 (tamper-evident hash chain) | PostgreSQL `pgcrypto` / `hashlib` | 256 bits |
| Release Receipt Signatures | RS256 (RSA with SHA-256) | PyJWT / `cryptography.hazmat.primitives.asymmetric.rsa` | 2048 bits |
| User Credential Hashing | Argon2id | `passlib.hash.argon2` | v=19, m=65536, t=3, p=4 |
| Bank Callback Gate | HMAC-SHA256 | `hmac` & `hashlib` | 256 bits |
