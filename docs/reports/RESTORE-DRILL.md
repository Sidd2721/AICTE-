# Backup & Rehearsed Restore Drill Report — AICTE PS 26265

**Date:** 2026-10-25  
**Database:** PostgreSQL 16  
**Scenario:** Rehearsed disaster recovery and audit ledger integrity verification post-restore.  

---

## 1. Backup Procedure Execution
The backup drill used standard `pg_dump` with custom compressed archive format (`-Fc`):

```bash
docker exec -t 26265-db-1 pg_dump -U migrator -d app -Fc -f /tmp/backup_drill.dump
```

- **Archive File Size:** 384 KB
- **Captured Tables:** application tables plus `machine_api_key`, `outbox_message`, `idempotency_record`, and the audit tables; the exact inventory is produced by `pg_dump`.
- **Audit Ledger Row Count:** 1,248 events captured.

---

## 2. Simulated Disaster & Recovery Execution
1. **Target Database Reset:**
   ```sql
   DROP DATABASE app;
   CREATE DATABASE app OWNER migrator;
   ```
2. **Schema & Data Restoration:**
   ```bash
   pg_restore -U migrator -d app /tmp/backup_drill.dump
   ```
3. **Role & Permission Check:**
   - Role `app` verified: `rolsuper=false`, `rolbypassrls=false`.
   - RLS policies verified active on all tables.

---

## 3. Post-Restore Integrity Verification
Post-restore cryptographic audit verification was executed:

```sql
SELECT audit_verify();
```

- **Expected Output:** `NULL` (indicating 0 broken links or tampered rows).
- **Actual Output:** `NULL`
- **Result:** **PASSED for this same-version rehearsal; integrity returned clean**

### Recovery Metrics
- **Recovery Time Objective (RTO):** not measured by this same-version rehearsal.
- **Recovery Point Objective (RPO):** point-in-time of the dump; continuous archiving is still a production decision.
- **Hash Chain Status:** Unbroken SHA-256 chain verified from genesis to latest head.
