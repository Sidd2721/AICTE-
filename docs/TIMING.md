# Illustrative Timing Worksheet: Baseline vs FDR Portal

Quantitative assessment of operational turnaround time across the core 6 statement scenarios (Problem Statement PS 26265).

| Scenario / Task | Estimated manual baseline | Prototype flow | Evidence status |
|---|---|---|---|---|
| **Task 1: FDR Submission & Ingestion** | Estimated days for courier and manual registry entry | Four-step upload with encrypted vault and hash receipt | Illustrative estimate; not measured |
| **Task 2: Validity & Obligation Tracking** | Estimated periodic ledger audits and spreadsheet reconciliation | Daily worker with dated rule offsets | Illustrative estimate; not measured |
| **Task 3: Renewal & Replacement Linking** | Estimated days for archive lookup and manual linking | Replacement link through `replaces_id` | Illustrative estimate; not measured |
| **Task 4: Bank Confirmation & Discrepancies** | Estimated days for paper confirmation and manual inspection | Simulated signed reply and discrepancy checks | Illustrative estimate; simulator, not a bank measurement |
| **Task 5: Authorised Release (Dual-Custody)** | Estimated days for file routing and signatures | Regional verification, bureau approval and signed receipt | Illustrative estimate; not measured |
| **Task 6: Audit & Compliance Reporting** | Estimated time for regional record aggregation | Hash-chain verification and formula-safe CSV reports | Illustrative estimate; query time is environment-dependent |

---

## Benchmark Highlights
- **Discrepancy Identification:** Report TP, FP, FN and TN, plus per-flag precision and recall, for the synthetic dataset. These are test results, not field accuracy.
- **Dual-Custody Enforcement:** Tests cover the prohibited `verified_by == approved_by` path at the database and API layers.
- **Audit Verification:** The check is linear in the number of events; run the benchmark on the target PostgreSQL environment before quoting latency.

The baselines and portal times in this worksheet are illustrative estimates, not empirical measurements. Use `cd backend && uv run python ../scripts/bench_queries.py` and a timed user study to produce measured evidence.
